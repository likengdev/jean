from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Sum
from django.utils import timezone
from django.contrib.auth.models import User
import datetime

from .models import Contribuable, Impot, Declaration, Paiement, Penalite, Notification, Profil
from .serializers import (
    ContribuableSerializer, ImpotSerializer, DeclarationSerializer,
    PaiementSerializer, PenaliteSerializer, RegisterSerializer,
    UserSerializer, NotificationSerializer
)
from .utils import (
    envoyer_notification_paiement,
    envoyer_notification_penalite,
    envoyer_notification_declaration
)

def get_role(user):
    try:
        return user.profil.role
    except Exception:
        return 'superadmin' if user.is_superuser else 'gestionnaire'

class RegisterView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        if get_role(request.user) != 'superadmin':
            return Response({'error': 'Seul le Super Administrateur peut créer des utilisateurs.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'message': f'Utilisateur {user.username} créé avec succès.',
                'username': user.username, 'email': user.email,
                'mot_de_passe': serializer.mot_de_passe_genere,
                'email_envoye': serializer.email_envoye,
                'erreur_email': serializer.erreur_email
            }, status=status.HTTP_201_CREATED)
        print("❌ REGISTER ERRORS:", serializer.errors)  # DEBUG
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    pagination_class = None

    def get_queryset(self):
        if get_role(self.request.user) != 'superadmin':
            return User.objects.none()
        return User.objects.all().select_related('profil')

class UserToggleActiveView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    queryset = User.objects.all().select_related('profil')

    def post(self, request, pk):
        if get_role(request.user) != 'superadmin':
            return Response({'error': 'Seul le Super Administrateur peut modifier les utilisateurs.'}, status=status.HTTP_403_FORBIDDEN)
        user_target = self.get_object()
        if user_target == request.user or user_target.is_superuser:
            return Response({'error': 'Action non autorisée.'}, status=status.HTTP_400_BAD_REQUEST)
        
        profil, _ = Profil.objects.get_or_create(user=user_target)
        activer_val = request.data.get('activer')
        if activer_val is None:
            nouveau_statut = not profil.est_actif
        elif isinstance(activer_val, str):
            nouveau_statut = activer_val.lower() in ('true', '1', 'yes')
        else:
            nouveau_statut = bool(activer_val)
        profil.est_actif = nouveau_statut
        profil.save()
        user_target.is_active = nouveau_statut
        user_target.save()
        return Response({'message': f'Utilisateur {user_target.username} {"activé" if nouveau_statut else "désactivé"}.', 'est_actif': nouveau_statut})

class ContribuableViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ContribuableSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['nom', 'prenom', 'nif', 'telephone', 'email']
    ordering_fields = ['date_enregistrement', 'nom']
    ordering = ['-date_enregistrement']

    def get_queryset(self):
        return Contribuable.objects.all() if get_role(self.request.user) == 'superadmin' else Contribuable.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ImpotViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ImpotSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['type_impot', 'contribuable__nom', 'contribuable__nif']
    ordering_fields = ['date_echeance', 'montant']
    ordering = ['-date_creation']

    def get_queryset(self):
        return Impot.objects.all() if get_role(self.request.user) == 'superadmin' else Impot.objects.filter(contribuable__user=self.request.user)

    @action(detail=False, methods=['get'])
    def statistiques(self, request):
        qs = self.get_queryset()
        return Response({
            'total_impots': qs.count(),
            'total_montant': float(qs.aggregate(Sum('montant'))['montant__sum'] or 0),
            'impots_payes': float(qs.filter(statut='paye').aggregate(Sum('montant'))['montant__sum'] or 0),
            'impots_en_retard': float(qs.filter(statut='en_retard').aggregate(Sum('montant'))['montant__sum'] or 0),
        })

class DeclarationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DeclarationSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['contribuable__nom', 'periode', 'statut']
    ordering_fields = ['date_soumission', 'date_creation']
    ordering = ['-date_creation']

    def get_queryset(self):
        return Declaration.objects.all() if get_role(self.request.user) == 'superadmin' else Declaration.objects.filter(contribuable__user=self.request.user)

    @action(detail=True, methods=['post'])
    def soumettre(self, request, pk=None):
        declaration = self.get_object()
        if declaration.statut != 'brouillon':
            return Response({'error': 'Seules les déclarations en brouillon peuvent être soumises.'}, status=status.HTTP_400_BAD_REQUEST)
        declaration.statut = 'soumise'
        declaration.date_soumission = timezone.now()
        declaration.save()
        envoyer_notification_declaration(declaration)
        return Response({'message': 'Déclaration soumise avec succès.'})

    @action(detail=True, methods=['post'])
    def valider(self, request, pk=None):
        declaration = self.get_object()
        if declaration.statut != 'soumise':
            return Response({'error': 'Seules les déclarations soumises peuvent être validées.'}, status=status.HTTP_400_BAD_REQUEST)
        declaration.statut = 'validee'
        declaration.save()
        envoyer_notification_declaration(declaration)
        return Response({'message': 'Déclaration validée.'})

    @action(detail=True, methods=['post'])
    def rejeter(self, request, pk=None):
        declaration = self.get_object()
        if declaration.statut != 'soumise':
            return Response({'error': 'Seules les déclarations soumises peuvent être rejetées.'}, status=status.HTTP_400_BAD_REQUEST)
        declaration.statut = 'rejetee'
        declaration.save()
        envoyer_notification_declaration(declaration)
        return Response({'message': 'Déclaration rejetée.'})

class PaiementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PaiementSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['reference', 'impot__contribuable__nom', 'mode_paiement']
    ordering_fields = ['date_paiement', 'montant_paye']
    ordering = ['-date_paiement']

    def get_queryset(self):
        return Paiement.objects.all() if get_role(self.request.user) == 'superadmin' else Paiement.objects.filter(impot__contribuable__user=self.request.user)

    def perform_create(self, serializer):
        paiement = serializer.save()
        total_paye = float(paiement.impot.paiements.aggregate(Sum('montant_paye'))['montant_paye__sum'] or 0)
        if total_paye >= float(paiement.impot.montant):
            paiement.impot.statut = 'paye'
            paiement.impot.save()
        envoyer_notification_paiement(paiement)

class PenaliteViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PenaliteSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['motif', 'impot__contribuable__nom']
    ordering = ['-date_application']

    def get_queryset(self):
        return Penalite.objects.all() if get_role(self.request.user) == 'superadmin' else Penalite.objects.filter(impot__contribuable__user=self.request.user)

    def perform_create(self, serializer):
        penalite = serializer.save()
        envoyer_notification_penalite(penalite)

class NotificationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
    filter_backends = [OrderingFilter]
    ordering_fields = ['date_envoi']
    ordering = ['-date_envoi']

    def get_queryset(self):
        return Notification.objects.all() if get_role(self.request.user) == 'superadmin' else Notification.objects.filter(contribuable__user=self.request.user)

class DashboardView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        role = get_role(user)
        is_super = role == 'superadmin'
        
        contribuables = Contribuable.objects.all() if is_super else Contribuable.objects.filter(user=user)
        impots = Impot.objects.all() if is_super else Impot.objects.filter(contribuable__user=user)
        paiements = Paiement.objects.all() if is_super else Paiement.objects.filter(impot__contribuable__user=user)
        penalites = Penalite.objects.all() if is_super else Penalite.objects.filter(impot__contribuable__user=user)
        declarations_recentes = Declaration.objects.order_by('-date_creation')[:3] if is_super else Declaration.objects.filter(contribuable__user=user).order_by('-date_creation')[:3]

        activite_recente = []
        for p in paiements.order_by('-date_paiement')[:3]:
            activite_recente.append({'type': 'paiement', 'message': f"Paiement {p.montant_paye} FCFA — {p.impot.contribuable.nom}", 'statut': 'paye', 'date': str(p.date_paiement)})
        for d in declarations_recentes:
            activite_recente.append({'type': 'declaration', 'message': f"Déclaration {d.contribuable.nom} — {d.periode}", 'statut': d.statut, 'date': str(d.date_creation)})

        return Response({
            'contribuables_enregistres': contribuables.count(),
            'total_impots_collectes': float(paiements.aggregate(Sum('montant_paye'))['montant_paye__sum'] or 0),
            'impots_impayes': float(impots.filter(statut__in=['en_attente', 'en_retard']).aggregate(Sum('montant'))['montant__sum'] or 0),
            'penalites_en_retard': float(penalites.filter(est_payee=False).aggregate(Sum('montant'))['montant__sum'] or 0),
            'activite_recente': activite_recente,
            'role': role,
        })

class RevenusMensuelView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        annee = int(request.query_params.get('annee', datetime.date.today().year))
        user = request.user
        role = get_role(user)
        queryset = Paiement.objects.filter(date_paiement__year=annee) if role == 'superadmin' else Paiement.objects.filter(impot__contribuable__user=user, date_paiement__year=annee)

        data = [0] * 12
        for paiement in queryset:
            data[paiement.date_paiement.month - 1] += float(paiement.montant_paye)

        return Response({'labels': ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc'], 'data': data, 'annee': annee})

class UserProfileView(generics.RetrieveAPIView):
    """Lecture seule stricte du profil de l'utilisateur connecté."""
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    def get_object(self):
        return self.request.user