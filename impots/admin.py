from django.contrib import admin
from .models import Profil, Contribuable, Impot, Declaration, Paiement, Penalite, Notification


@admin.register(Profil)
class ProfilAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'est_actif', 'date_creation']
    list_filter = ['role', 'est_actif']
    search_fields = ['user__username', 'user__email']


@admin.register(Contribuable)
class ContribuableAdmin(admin.ModelAdmin):
    list_display = ['nom', 'prenom', 'nif', 'type_contribuable', 'telephone', 'date_enregistrement']
    search_fields = ['nom', 'prenom', 'nif']
    list_filter = ['type_contribuable']


@admin.register(Impot)
class ImpotAdmin(admin.ModelAdmin):
    list_display = ['contribuable', 'type_impot', 'montant', 'statut', 'date_echeance']
    search_fields = ['contribuable__nom', 'type_impot']
    list_filter = ['statut', 'type_impot']


@admin.register(Declaration)
class DeclarationAdmin(admin.ModelAdmin):
    list_display = ['contribuable', 'impot', 'periode', 'montant_declare', 'statut']
    search_fields = ['contribuable__nom']
    list_filter = ['statut']


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ['impot', 'montant_paye', 'mode_paiement', 'reference', 'date_paiement']
    search_fields = ['reference', 'impot__contribuable__nom']
    list_filter = ['mode_paiement']


@admin.register(Penalite)
class PenaliteAdmin(admin.ModelAdmin):
    list_display = ['impot', 'montant', 'est_payee', 'date_application']
    list_filter = ['est_payee']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['contribuable', 'type_notification', 'sujet', 'email_envoye', 'date_envoi']
    list_filter = ['type_notification', 'email_envoye']