from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db import IntegrityError

from .models import Voter, Election, Position, Candidate, Vote
from .face_utils import detect_face_in_image, compare_faces
from .serializers import ElectionSerializer, ElectionListSerializer, PositionSerializer


# ─── AUTH ────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def register(request):
    data = request.data
    face = request.FILES.get('face')
    id_proof_image = request.FILES.get('id_proof_image')

    if not face:
        return Response({'error': 'Face image is required.'}, status=400)
    if not id_proof_image:
        return Response({'error': 'ID proof image is required.'}, status=400)

    face_result = detect_face_in_image(face)
    if not face_result['success']:
        return Response({'error': f"Face detection failed: {face_result['message']}"}, status=400)

    if Voter.objects.filter(id_proof_number=data.get('id_proof_number')).exists():
        return Response({'error': 'This ID proof number is already registered.'}, status=400)

    try:
        voter = Voter.objects.create(
            full_name=data['full_name'],
            date_of_birth=data['date_of_birth'],
            gender=data['gender'],
            email=data['email'],
            mobile_number=data['mobile_number'],
            address=data['address'],
            voter_id=data['voter_id'],
            id_proof_type=data['id_proof_type'],
            id_proof_number=data['id_proof_number'],
            id_proof_image=id_proof_image,
            username=data['username'],
            password=data['password'],
            face_image=face,
            face_encoding=face_result['encoding'],
            face_detected=True,
            face_detection_confidence=face_result['confidence'],
            is_verified=False,
            verification_status='PENDING',
        )
        return Response({
            'message': f'Registration successful! Face detected with {face_result["confidence"]}% confidence. Pending admin verification.',
            'voter_id': voter.id,
        }, status=201)
    except IntegrityError as e:
        err = str(e)
        if 'email' in err:
            msg = 'Email already registered.'
        elif 'voter_id' in err:
            msg = 'Voter ID already registered.'
        elif 'username' in err:
            msg = 'Username already taken.'
        else:
            msg = 'Registration failed. Check your details.'
        return Response({'error': msg}, status=400)


@api_view(['POST'])
@parser_classes([JSONParser, FormParser])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')

    try:
        user = Voter.objects.get(username=username, password=password)
    except Voter.DoesNotExist:
        return Response({'error': 'Invalid credentials.'}, status=401)

    if not user.face_detected:
        return Response({'error': 'Account registration incomplete. Face detection failed.'}, status=403)

    if not user.is_verified or user.verification_status != 'APPROVED':
        status_map = {
            'PENDING': 'Your account is pending admin verification.',
            'REJECTED': f'Your account was rejected. {user.admin_remarks or "Contact admin."}',
        }
        return Response({'error': status_map.get(user.verification_status, 'Account not verified.')}, status=403)

    try:
        election = Election.objects.get(is_active=True)
    except Election.DoesNotExist:
        return Response({'error': 'No active election at the moment.'}, status=403)

    if not election.is_ongoing():
        return Response({'error': f'Election "{election.title}" is {election.status().lower()}.'}, status=403)

    if user.has_voted_in_election(election):
        return Response({'error': f'You have already voted in "{election.title}".'}, status=403)

    # Store pending user in session
    request.session['pending_user_id'] = user.id
    return Response({'message': 'Credentials verified. Proceed to face verification.', 'user_id': user.id})


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def face_verification(request):
    pending_user_id = request.session.get('pending_user_id')
    if not pending_user_id:
        return Response({'error': 'Please login first.'}, status=401)

    captured_face = request.FILES.get('captured_face')
    if not captured_face:
        return Response({'error': 'No face image provided.'}, status=400)

    try:
        user = Voter.objects.get(id=pending_user_id)
    except Voter.DoesNotExist:
        return Response({'error': 'User not found.'}, status=404)

    face_result = detect_face_in_image(captured_face)
    if not face_result['success']:
        return Response({'error': f"Face detection failed: {face_result['message']}"}, status=400)

    if not user.face_encoding:
        return Response({'error': 'No face encoding in profile. Contact admin.'}, status=400)

    comparison = compare_faces(user.face_encoding, face_result['encoding'], threshold=0.5)
    if comparison['match']:
        request.session['user_id'] = user.id
        del request.session['pending_user_id']
        return Response({
            'message': f'Face verified! Similarity: {comparison["similarity"]*100:.1f}%',
            'user_id': user.id,
        })
    else:
        return Response({
            'error': f'Face does not match. Similarity: {comparison["similarity"]*100:.1f}%',
        }, status=403)


@api_view(['POST'])
def logout(request):
    request.session.flush()
    return Response({'message': 'Logged out successfully.'})


# ─── ELECTIONS ───────────────────────────────────────────────────────────────

@api_view(['GET'])
def elections(request):
    now = timezone.now()
    active = Election.objects.filter(is_active=True, start_date__lte=now, end_date__gte=now).first()
    upcoming = Election.objects.filter(start_date__gt=now).order_by('start_date')[:5]
    past = Election.objects.filter(end_date__lt=now).order_by('-end_date')[:5]

    return Response({
        'active': ElectionListSerializer(active, context={'request': request}).data if active else None,
        'upcoming': ElectionListSerializer(upcoming, many=True, context={'request': request}).data,
        'past': ElectionListSerializer(past, many=True, context={'request': request}).data,
    })


@api_view(['GET'])
def election_detail(request, pk):
    try:
        election = Election.objects.get(pk=pk)
    except Election.DoesNotExist:
        return Response({'error': 'Election not found.'}, status=404)
    return Response(ElectionSerializer(election, context={'request': request}).data)


# ─── VOTING ──────────────────────────────────────────────────────────────────

@api_view(['GET'])
def vote_page(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return Response({'error': 'Not authenticated.'}, status=401)

    try:
        user = Voter.objects.get(id=user_id)
        election = Election.objects.get(is_active=True)
    except Voter.DoesNotExist:
        return Response({'error': 'User not found.'}, status=404)
    except Election.DoesNotExist:
        return Response({'error': 'No active election.'}, status=404)

    if not election.is_ongoing():
        return Response({'error': f'Election is {election.status().lower()}.'}, status=403)

    if user.has_voted_in_election(election):
        votes = Vote.objects.filter(voter=user, election=election).select_related('candidate__position')
        return Response({
            'already_voted': True,
            'election': ElectionListSerializer(election).data,
            'votes_cast': [f"{v.candidate.position.title}: {v.candidate.name}" for v in votes],
        })

    positions = Position.objects.filter(election=election).prefetch_related('candidates')
    return Response({
        'already_voted': False,
        'election': ElectionListSerializer(election).data,
        'positions': PositionSerializer(positions, many=True, context={'request': request}).data,
    })


@api_view(['POST'])
@parser_classes([JSONParser])
def submit_vote(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return Response({'error': 'Not authenticated.'}, status=401)

    try:
        user = Voter.objects.get(id=user_id)
        election = Election.objects.get(is_active=True)
    except (Voter.DoesNotExist, Election.DoesNotExist):
        return Response({'error': 'User or election not found.'}, status=404)

    if not election.is_ongoing():
        return Response({'error': 'Election is not active.'}, status=403)

    if user.has_voted_in_election(election):
        return Response({'error': 'You have already voted.'}, status=403)

    # votes: { "position_<id>": candidate_id, ... }
    votes_data = request.data.get('votes', {})
    positions = Position.objects.filter(election=election)
    votes_to_create = []

    for position in positions:
        candidate_id = votes_data.get(f'position_{position.id}')
        if candidate_id:
            try:
                candidate = Candidate.objects.get(id=candidate_id, position=position)
                votes_to_create.append(Vote(voter=user, candidate=candidate, election=election))
            except Candidate.DoesNotExist:
                return Response({'error': f'Invalid candidate for {position.title}.'}, status=400)

    if not votes_to_create:
        return Response({'error': 'Select at least one candidate.'}, status=400)

    Vote.objects.bulk_create(votes_to_create)
    user.voted = True
    user.save()

    return Response({
        'message': 'Votes submitted successfully!',
        'votes_cast': [f"{v.candidate.position.title}: {v.candidate.name}" for v in votes_to_create],
    })


# ─── RESULTS ─────────────────────────────────────────────────────────────────

def _build_results(election):
    positions = Position.objects.filter(election=election).prefetch_related('candidates')
    total_voters = Voter.objects.filter(is_verified=True, verification_status='APPROVED').count()
    total_votes_cast = Vote.objects.filter(election=election).values('voter').distinct().count()

    results_data = []
    for position in positions:
        candidates_data = []
        position_total = 0

        for candidate in position.candidates.all():
            count = Vote.objects.filter(candidate=candidate, election=election).count()
            position_total += count
            candidates_data.append({'id': candidate.id, 'name': candidate.name, 'party': candidate.party, 'votes': count, 'percentage': 0})

        winner = None
        max_votes = 0
        for d in candidates_data:
            if position_total > 0:
                d['percentage'] = round((d['votes'] / position_total) * 100, 1)
            if d['votes'] > max_votes:
                max_votes = d['votes']
                winner = d['name']

        results_data.append({
            'position': position.title,
            'candidates': candidates_data,
            'winner': winner,
            'total_votes': position_total,
        })

    return {
        'election': {'id': election.id, 'title': election.title, 'end_date': election.end_date},
        'results': results_data,
        'total_voters': total_voters,
        'total_votes_cast': total_votes_cast,
        'participation_rate': round((total_votes_cast / total_voters * 100) if total_voters > 0 else 0, 1),
    }


@api_view(['GET'])
def results(request):
    user_id = request.session.get('user_id')
    election_id = request.GET.get('election_id')

    election = Election.objects.get(pk=election_id) if election_id else Election.objects.order_by('-created_at').first()
    if not election:
        return Response({'error': 'No elections found.'}, status=404)

    now = timezone.now()
    if user_id and now < election.end_date:
        return Response({'error': 'Results available after election ends.'}, status=403)

    return Response(_build_results(election))


@api_view(['GET'])
def admin_results(request):
    if not request.session.get('is_admin'):
        return Response({'error': 'Admin access required.'}, status=403)

    election_id = request.GET.get('election_id')
    election = Election.objects.get(pk=election_id) if election_id else (
        Election.objects.filter(is_active=True).first() or Election.objects.order_by('-created_at').first()
    )
    if not election:
        return Response({'error': 'No elections found.'}, status=404)

    data = _build_results(election)
    data['all_elections'] = list(Election.objects.values('id', 'title').order_by('-created_at'))
    return Response(data)
