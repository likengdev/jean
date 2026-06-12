import random
import string
from rest_framework import serializers
from django.contrib.auth.models import User
from django.conf import settings
from .models import Profil, Contribuable, Impot, Declaration, Paiement, Penalite, Notification
from .email_service import envoyer_identifiants_async

MOT_DE_PASSE_PAR_DEFAUT = {
    'admin': 'Admin2026',
    'gestionnaire': 'Gestionnaire2026',
}

def generer_mot_de_passe(role='gestionnaire'):
    """Retourne le mot de passe par défaut selon le rôle."""
    return MOT_DE_PASSE_PAR_DEFAUT.get(role, 'GestImpots2026')

class ProfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profil
        fields = ['role', 'telephone', 'est_actif', 'date_creation']

class UserSerializer(serializers.ModelSerializer):
    profil = ProfilSerializer(read_only=True)
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profil']

class RegisterSerializer(serializers.Serializer):
    username   = serializers.CharField(max_length=150)
    role       = serializers.ChoiceField(choices=['admin', 'gestionnaire'], default='gestionnaire')
    first_name = serializers.CharField(max_length=150, required=False, default='')
    last_name  = serializers.CharField(max_length=150, required=False, default='')
    email      = serializers.EmailField(required=False, allow_null=True, default=None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mot_de_passe_genere = None
        self.email_envoye = False
        self.erreur_email = None

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Ce nom d'utilisateur existe déjà.")
        return value

    def validate_email(self, value):
        if not value:
            return None
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Cet email est déjà utilisé.")
        return value

    def create(self, validated_data):
        role       = validated_data.get('role', 'gestionnaire')
        mot_de_passe = generer_mot_de_passe(role)
        self.mot_de_passe_genere = mot_de_passe

        user = User.objects.create_user(
            username   = validated_data['username'],
            email      = validated_data.get('email') or '',
            first_name = validated_data.get('first_name', ''),
            last_name  = validated_data.get('last_name', ''),
            password   = mot_de_passe
        )

        profil, _ = Profil.objects.get_or_create(user=user)
        profil.role = role
        profil.save()

        role_labels = {'admin': 'Chef de Bureau', 'gestionnaire': 'Agent Fiscal'}

        if user.email:
            try:
                envoyer_identifiants_async(
                    user.username, user.email, user.first_name,
                    mot_de_passe, role_labels.get(role, role),
                )
                self.email_envoye = True
            except Exception as e:
                self.email_envoye = False
                self.erreur_email = str(e)

        return user

class ContribuableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contribuable
        fields = ['id', 'nom', 'prenom', 'nif', 'type_contribuable', 'adresse', 'telephone', 'email', 'date_enregistrement']
        read_only_fields = ['date_enregistrement']

    def validate_nif(self, value):
        if len(value) < 3:
            raise serializers.ValidationError("Le NIF doit contenir au moins 3 caractères.")
        return value

class ImpotSerializer(serializers.ModelSerializer):
    contribuable_nom = serializers.CharField(source='contribuable.nom', read_only=True)

    class Meta:
        model = Impot
        fields = ['id', 'contribuable', 'contribuable_nom', 'type_impot', 'montant', 'date_echeance', 'statut', 'description', 'date_creation', 'date_modification']
        read_only_fields = ['date_creation', 'date_modification']

    def validate_montant(self, value):
        if value <= 0:
            raise serializers.ValidationError("Le montant doit être supérieur à 0.")
        return value

class DeclarationSerializer(serializers.ModelSerializer):
    contribuable_nom = serializers.CharField(source='contribuable.nom', read_only=True)

    class Meta:
        model = Declaration
        fields = ['id', 'contribuable', 'contribuable_nom', 'impot', 'periode', 'montant_declare', 'statut', 'date_soumission', 'date_creation']
        read_only_fields = ['date_creation']

    def validate_montant_declare(self, value):
        if value <= 0:
            raise serializers.ValidationError("Le montant déclaré doit être supérieur à 0.")
        return value

class PaiementSerializer(serializers.ModelSerializer):
    contribuable_nom = serializers.CharField(source='impot.contribuable.nom', read_only=True)

    class Meta:
        model = Paiement
        fields = ['id', 'impot', 'contribuable_nom', 'montant_paye', 'mode_paiement', 'reference', 'date_paiement', 'commentaire']
        read_only_fields = ['date_paiement']

    def validate_montant_paye(self, value):
        if value <= 0:
            raise serializers.ValidationError("Le montant payé doit être supérieur à 0.")
        return value

    def validate_reference(self, value):
        instance = self.instance
        qs = Paiement.objects.filter(reference=value)
        if instance:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Cette référence existe déjà.")
        return value

class PenaliteSerializer(serializers.ModelSerializer):
    contribuable_nom = serializers.CharField(source='impot.contribuable.nom', read_only=True)

    class Meta:
        model = Penalite
        fields = ['id', 'impot', 'contribuable_nom', 'montant', 'motif', 'date_application', 'est_payee']
        read_only_fields = ['date_application']

    def validate_montant(self, value):
        if value <= 0:
            raise serializers.ValidationError("Le montant doit être supérieur à 0.")
        return value

class NotificationSerializer(serializers.ModelSerializer):
    contribuable_nom = serializers.CharField(source='contribuable.nom', read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'contribuable', 'contribuable_nom', 'type_notification', 'sujet', 'message', 'email_envoye', 'date_envoi']
        read_only_fields = ['date_envoi', 'email_envoye']