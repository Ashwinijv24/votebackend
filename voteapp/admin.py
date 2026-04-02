from django.contrib import admin
from .models import Voter, Election, Position, Candidate, Vote
from django.utils.html import format_html
from django.utils import timezone

# Inline admins for related models
class PositionInline(admin.TabularInline):
    model = Position
    extra = 1
    fields = ['title', 'description', 'order', 'max_votes']

class CandidateInline(admin.TabularInline):
    model = Candidate
    extra = 1
    fields = ['name', 'party', 'photo', 'symbol', 'bio', 'order']

@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'status_badge', 'start_date', 'end_date', 'is_active', 'created_at']
    list_filter = ['is_active', 'start_date', 'end_date']
    search_fields = ['title', 'description']
    inlines = [PositionInline]
    
    fieldsets = (
        ('Election Details', {
            'fields': ('title', 'description')
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date', 'is_active'),
            'description': 'Set the voting period. Only one election can be active at a time.'
        }),
    )
    
    def status_badge(self, obj):
        status = obj.status()
        colors = {
            'Active': '#28a745',
            'Scheduled': '#ffc107',
            'Ended': '#6c757d',
            'Inactive': '#dc3545'
        }
        color = colors.get(status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            status
        )
    status_badge.short_description = 'Status'
    
    def save_model(self, request, obj, form, change):
        # Ensure only one election is active at a time
        if obj.is_active:
            Election.objects.exclude(pk=obj.pk).update(is_active=False)
        super().save_model(request, obj, form, change)

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ['title', 'election', 'order', 'max_votes', 'candidate_count']
    list_filter = ['election']
    search_fields = ['title', 'election__title']
    inlines = [CandidateInline]
    
    def candidate_count(self, obj):
        count = obj.candidates.count()
        return format_html('<strong>{}</strong> candidates', count)
    candidate_count.short_description = 'Candidates'

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ['name', 'party', 'position', 'election_title', 'order', 'vote_count_display', 'photo_preview', 'symbol_preview']
    list_filter = ['position__election', 'position', 'party']
    search_fields = ['name', 'position__title', 'party']
    
    fieldsets = (
        ('Candidate Information', {
            'fields': ('position', 'name', 'party', 'photo', 'symbol', 'bio', 'order')
        }),
    )
    
    def election_title(self, obj):
        return obj.position.election.title
    election_title.short_description = 'Election'
    
    def vote_count_display(self, obj):
        count = obj.vote_count()
        return format_html('<strong style="color: #28a745;">{}</strong> votes', count)
    vote_count_display.short_description = 'Votes'
    
    def photo_preview(self, obj):
        if obj.photo:
            return format_html('<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 50%;" />', obj.photo.url)
        return "No photo"
    photo_preview.short_description = 'Photo'
    
    def symbol_preview(self, obj):
        if obj.symbol:
            return format_html('<img src="{}" style="width: 40px; height: 40px; object-fit: contain;" />', obj.symbol.url)
        return "No symbol"
    symbol_preview.short_description = 'Symbol'

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ['voter_name', 'candidate', 'position_title', 'election_title', 'timestamp']
    list_filter = ['election', 'candidate__position', 'timestamp']
    search_fields = ['voter__username', 'voter__full_name', 'candidate__name']
    readonly_fields = ['voter', 'candidate', 'election', 'timestamp']
    
    def voter_name(self, obj):
        return obj.voter.full_name
    voter_name.short_description = 'Voter'
    
    def position_title(self, obj):
        return obj.candidate.position.title
    position_title.short_description = 'Position'
    
    def election_title(self, obj):
        return obj.election.title
    election_title.short_description = 'Election'
    
    def has_add_permission(self, request):
        # Prevent manual vote creation
        return False
    
    def has_change_permission(self, request, obj=None):
        # Prevent vote modification
        return False

@admin.register(Voter)
class VoterAdmin(admin.ModelAdmin):
    list_display = ['username', 'full_name', 'email', 'id_proof_type', 'face_status', 'verification_status_badge', 'voted', 'created_at']
    list_filter = ['verification_status', 'is_verified', 'voted', 'id_proof_type', 'gender']
    search_fields = ['username', 'full_name', 'email', 'voter_id', 'id_proof_number', 'mobile_number']
    readonly_fields = ['created_at', 'updated_at', 'view_face_image', 'view_id_proof_image', 'full_name', 'date_of_birth', 'gender', 'email', 'mobile_number', 'address', 'voter_id', 'id_proof_type', 'id_proof_number', 'username', 'password', 'face_image', 'id_proof_image', 'face_encoding', 'face_detected', 'face_detection_confidence']
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('full_name', 'date_of_birth', 'gender')
        }),
        ('Contact Information', {
            'fields': ('email', 'mobile_number', 'address')
        }),
        ('Identification', {
            'fields': ('voter_id', 'id_proof_type', 'id_proof_number', 'view_id_proof_image')
        }),
        ('Verification Status - EDIT THIS SECTION', {
            'fields': ('verification_status', 'is_verified', 'admin_remarks', 'verified_at'),
            'classes': ('wide',),
            'description': 'Only modify the verification status fields below'
        }),
        ('Account Credentials', {
            'fields': ('username', 'password'),
            'classes': ('collapse',)
        }),
        ('Biometric', {
            'fields': ('view_face_image', 'face_detected', 'face_detection_confidence'),
            'classes': ('collapse',)
        }),
        ('Voting Status', {
            'fields': ('voted',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_voters', 'reject_voters', 'mark_pending']
    
    def face_status(self, obj):
        if obj.face_detected:
            confidence = round(float(obj.face_detection_confidence), 1)
            return format_html(
                '<span style="color: green;">✓ Detected ({}%)</span>',
                confidence
            )
        return format_html('<span style="color: red;">✗ Not Detected</span>')
    face_status.short_description = 'Face Detection'
    
    def verification_status_badge(self, obj):
        colors = {
            'PENDING': '#ffc107',
            'APPROVED': '#28a745',
            'REJECTED': '#dc3545'
        }
        color = colors.get(obj.verification_status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_verification_status_display()
        )
    verification_status_badge.short_description = 'Status'
    
    def view_face_image(self, obj):
        if obj.face_image:
            return format_html('<img src="{}" style="max-width: 200px; max-height: 200px;" />', obj.face_image.url)
        return "No image"
    view_face_image.short_description = 'Face Image'
    
    def view_id_proof_image(self, obj):
        if obj.id_proof_image:
            return format_html(
                '<div><img src="{}" style="max-width: 400px; max-height: 400px;" /><br><strong>ID Type:</strong> {}<br><strong>ID Number:</strong> {}</div>',
                obj.id_proof_image.url,
                obj.get_id_proof_type_display(),
                obj.id_proof_number
            )
        return "No image"
    view_id_proof_image.short_description = 'ID Proof Image'
    
    def approve_voters(self, request, queryset):
        updated = queryset.update(
            verification_status='APPROVED',
            is_verified=True,
            verified_at=timezone.now()
        )
        self.message_user(request, f'{updated} voter(s) approved successfully.')
    approve_voters.short_description = '✅ Approve selected voters'
    
    def reject_voters(self, request, queryset):
        updated = queryset.update(
            verification_status='REJECTED',
            is_verified=False
        )
        self.message_user(request, f'{updated} voter(s) rejected.')
    reject_voters.short_description = '❌ Reject selected voters'
    
    def mark_pending(self, request, queryset):
        updated = queryset.update(
            verification_status='PENDING',
            is_verified=False,
            verified_at=None
        )
        self.message_user(request, f'{updated} voter(s) marked as pending.')
    mark_pending.short_description = '⏳ Mark as pending verification'
    
    def save_model(self, request, obj, form, change):
        # Auto-set verified_at when approving
        if obj.verification_status == 'APPROVED' and obj.is_verified and not obj.verified_at:
            obj.verified_at = timezone.now()
        super().save_model(request, obj, form, change)
    
    def has_add_permission(self, request):
        # Disable adding voters from admin - they should register through the form
        return False
