from rest_framework import serializers
from .models import Voter, Election, Position, Candidate, Vote


class CandidateSerializer(serializers.ModelSerializer):
    vote_count = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    symbol_url = serializers.SerializerMethodField()

    class Meta:
        model = Candidate
        fields = ['id', 'name', 'party', 'bio', 'photo_url', 'symbol_url', 'vote_count']

    def get_vote_count(self, obj):
        return obj.votes.count()

    def get_photo_url(self, obj):
        request = self.context.get('request')
        if obj.photo and request:
            return request.build_absolute_uri(obj.photo.url)
        return None

    def get_symbol_url(self, obj):
        request = self.context.get('request')
        if obj.symbol and request:
            return request.build_absolute_uri(obj.symbol.url)
        return None


class PositionSerializer(serializers.ModelSerializer):
    candidates = CandidateSerializer(many=True, read_only=True)

    class Meta:
        model = Position
        fields = ['id', 'title', 'description', 'order', 'candidates']


class ElectionSerializer(serializers.ModelSerializer):
    positions = PositionSerializer(many=True, read_only=True)
    status = serializers.SerializerMethodField()
    total_votes = serializers.SerializerMethodField()

    class Meta:
        model = Election
        fields = ['id', 'title', 'description', 'start_date', 'end_date',
                  'is_active', 'status', 'positions', 'total_votes']

    def get_status(self, obj):
        return obj.status()

    def get_total_votes(self, obj):
        return obj.votes.count()


class ElectionListSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    position_count = serializers.SerializerMethodField()
    total_votes = serializers.SerializerMethodField()

    class Meta:
        model = Election
        fields = ['id', 'title', 'description', 'start_date', 'end_date',
                  'is_active', 'status', 'position_count', 'total_votes']

    def get_status(self, obj):
        return obj.status()

    def get_position_count(self, obj):
        return obj.positions.count()

    def get_total_votes(self, obj):
        return obj.votes.count()


class VoterRegisterSerializer(serializers.ModelSerializer):
    face = serializers.ImageField(write_only=True)

    class Meta:
        model = Voter
        fields = [
            'full_name', 'date_of_birth', 'gender', 'email',
            'mobile_number', 'address', 'voter_id',
            'id_proof_type', 'id_proof_number', 'id_proof_image',
            'username', 'password', 'face',
        ]
        extra_kwargs = {'password': {'write_only': True}}
