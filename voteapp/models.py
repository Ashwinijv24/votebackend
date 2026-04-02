
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
import os

def validate_image_format(value):
    ext = os.path.splitext(value.name)[1].lower()
    valid_extensions = ['.jpg', '.jpeg', '.png']
    if ext not in valid_extensions:
        raise ValidationError('Only JPEG and PNG files are allowed.')

class Election(models.Model):
    """Election model to manage voting periods"""
    title = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=False, help_text="Only one election can be active at a time")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    def is_ongoing(self):
        """Check if election is currently in voting period"""
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date
    
    def status(self):
        """Get election status"""
        now = timezone.now()
        if not self.is_active:
            return "Inactive"
        elif now < self.start_date:
            return "Scheduled"
        elif now > self.end_date:
            return "Ended"
        else:
            return "Active"
    
    def clean(self):
        """Validate election dates"""
        if self.start_date and self.end_date:
            if self.end_date <= self.start_date:
                raise ValidationError('End date must be after start date.')
    
    class Meta:
        ordering = ['-created_at']

class Position(models.Model):
    """Position/Role in election (President, Secretary, etc.)"""
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='positions')
    title = models.CharField(max_length=100, help_text="e.g., President, Secretary, Treasurer")
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0, help_text="Display order")
    max_votes = models.IntegerField(default=1, help_text="Maximum votes a voter can cast for this position")
    
    def __str__(self):
        return f"{self.title} - {self.election.title}"
    
    class Meta:
        ordering = ['election', 'order', 'title']
        unique_together = ['election', 'title']

class Candidate(models.Model):
    """Candidate running for a position"""
    position = models.ForeignKey(Position, on_delete=models.CASCADE, related_name='candidates')
    name = models.CharField(max_length=200)
    photo = models.ImageField(upload_to='candidates/', validators=[validate_image_format], blank=True, null=True)
    symbol = models.ImageField(upload_to='candidate_symbols/', validators=[validate_image_format], blank=True, null=True, help_text="Candidate election symbol")
    party = models.CharField(max_length=100, blank=True, help_text="Political party or group (optional)")
    bio = models.TextField(blank=True, help_text="Candidate biography/manifesto")
    order = models.IntegerField(default=0, help_text="Display order")
    
    def __str__(self):
        return f"{self.name} - {self.position.title}"
    
    def vote_count(self):
        """Get total votes for this candidate"""
        return self.votes.count()
    
    class Meta:
        ordering = ['position', 'order', 'name']

class Voter(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    
    ID_PROOF_CHOICES = [
        ('AADHAAR', 'Aadhaar Card'),
        ('COLLEGE', 'College ID Card'),
        ('PAN', 'PAN Card'),
        ('VOTER', 'Government-issued Voter ID'),
    ]
    
    VERIFICATION_STATUS = [
        ('PENDING', 'Pending Verification'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    
    # Personal Information
    full_name = models.CharField(max_length=200)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    
    # Contact Information
    email = models.EmailField(unique=True)
    mobile_number = models.CharField(max_length=15)
    address = models.TextField()
    
    # Identification
    voter_id = models.CharField(max_length=50, unique=True, help_text="Unique Voter ID or Institutional ID")
    
    # ID Proof Upload and Verification
    id_proof_type = models.CharField(max_length=20, choices=ID_PROOF_CHOICES)
    id_proof_number = models.CharField(max_length=50, unique=True, help_text="ID Proof Number (must be unique)")
    id_proof_image = models.ImageField(upload_to='id_proofs/', validators=[validate_image_format])
    
    # Verification Status
    is_verified = models.BooleanField(default=False)
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='PENDING')
    admin_remarks = models.TextField(blank=True, null=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    
    # Account Credentials
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)
    
    # Biometric - Face Recognition
    face_image = models.ImageField(upload_to='faces/', validators=[validate_image_format])
    face_encoding = models.TextField(blank=True, null=True, help_text="Facial feature encoding data")
    face_detected = models.BooleanField(default=False, help_text="Whether a valid face was detected")
    face_detection_confidence = models.FloatField(default=0.0, help_text="Face detection confidence score")
    
    # Voting Status - DEPRECATED (now tracked per election)
    voted = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.full_name} ({self.username}) - {self.verification_status}"
    
    def has_voted_in_election(self, election):
        """Check if voter has voted in specific election"""
        return Vote.objects.filter(voter=self, candidate__position__election=election).exists()
    
    class Meta:
        ordering = ['-created_at']

class Vote(models.Model):
    """Vote cast by a voter for a candidate"""
    voter = models.ForeignKey(Voter, on_delete=models.CASCADE, related_name='cast_votes')
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='votes')
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='votes')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.voter.username} voted for {self.candidate.name}"
    
    class Meta:
        unique_together = ['voter', 'candidate']  # Prevent duplicate votes
        ordering = ['-timestamp']
