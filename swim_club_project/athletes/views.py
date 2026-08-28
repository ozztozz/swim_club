# athletes/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Athlete
from .serializers import AthleteSerializer

class AthleteViewSet(viewsets.ModelViewSet):
    serializer_class = AthleteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_club_admin or user.is_coach or user.is_finance:
            return Athlete.objects.all()
        if user.is_parent:
            return Athlete.objects.filter(parent=user)
        return Athlete.objects.none()

    def perform_create(self, serializer):
        # Veli oluşturuyorsa: Onay bekliyor (is_active=False, status='pending')
        if self.request.user.is_parent:
            serializer.save(
                parent=self.request.user, 
                is_active=False, 
                status='pending'
            )
        else:
            # Yönetici ekliyorsa: Doğrudan onaylı ve aktif
            parent_id = self.request.data.get('parent')
            serializer.save(
                parent_id=parent_id if parent_id else self.request.user.id,
                is_active=True,
                status='approved'
            )

    # --- YÖNETİCİ ONAY AKSİYONLARI ---

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def approve(self, request, pk=None):
        """Yöneticinin sporcuyu onaylama endpoint'i: /api/athletes/{id}/approve/"""
        if not (request.user.is_club_admin or request.user.is_coach):
            return Response({'detail': 'Bu işlem için yetkiniz yok.'}, status=status.HTTP_403_FORBIDDEN)
        
        athlete = self.get_object()
        athlete.status = 'approved'
        athlete.is_active = True
        athlete.save()
        return Response({'status': 'Sporcu onaylandı ve aktif edildi.'})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def reject(self, request, pk=None):
        """Yöneticinin sporcuyu reddetme endpoint'i: /api/athletes/{id}/reject/"""
        if not (request.user.is_club_admin or request.user.is_coach):
            return Response({'detail': 'Bu işlem için yetkiniz yok.'}, status=status.HTTP_403_FORBIDDEN)
        
        athlete = self.get_object()
        athlete.status = 'rejected'
        athlete.is_active = False
        athlete.save()
        return Response({'status': 'Sporcu kaydı reddedildi.'})