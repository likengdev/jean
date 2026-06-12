from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profil(models.Model):
    ROLE_CHOICES = [
        ('superadmin', 'Super Administrateur'),
        ('admin', 'Administrateur'),
        ('gestionnaire', 'Gestionnaire'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profil')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='gestionnaire')
    telephone = models.CharField(max_length=20, blank=True)
    est_actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"

    class Meta:
        ordering = ['-date_creation']

@receiver(post_save, sender=User)
def creer_ou_sauvegarder_profil(sender, instance, created, **kwargs):
    """Garantit qu'un utilisateur a TOUJOURS un profil, même en cas de promotion superuser."""
    if created:
        role = 'superadmin' if instance.is_superuser else 'gestionnaire'
        Profil.objects.get_or_create(user=instance, defaults={'role': role})
    else:
        profil, _ = Profil.objects.get_or_create(user=instance)
        if instance.is_superuser and profil.role != 'superadmin':
            profil.role = 'superadmin'
            profil.save()

class Contribuable(models.Model):
    TYPE_CHOICES = [('particulier', 'Particulier'), ('entreprise', 'Entreprise')]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contribuables')
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100, blank=True)
    nif = models.CharField(max_length=50, unique=True)
    type_contribuable = models.CharField(max_length=20, choices=TYPE_CHOICES, default='particulier')
    adresse = models.TextField(blank=True)
    telephone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    date_enregistrement = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nom} {self.prenom} - {self.nif}"

    class Meta:
        ordering = ['-date_enregistrement']

class Impot(models.Model):
    TYPE_CHOICES = [('revenu', 'Impôt sur le revenu'), ('societe', 'Impôt sur les sociétés'), ('tva', 'TVA'), ('foncier', 'Impôt foncier'), ('autre', 'Autre')]
    STATUT_CHOICES = [('en_attente', 'En attente'), ('paye', 'Payé'), ('en_retard', 'En retard'), ('annule', 'Annulé')]
    contribuable = models.ForeignKey(Contribuable, on_delete=models.CASCADE, related_name='impots')
    type_impot = models.CharField(max_length=20, choices=TYPE_CHOICES)
    montant = models.DecimalField(max_digits=15, decimal_places=2)
    date_echeance = models.DateField()
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    description = models.TextField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.type_impot} - {self.contribuable.nom} - {self.montant} FCFA"

    class Meta:
        ordering = ['-date_creation']

class Declaration(models.Model):
    STATUT_CHOICES = [('brouillon', 'Brouillon'), ('soumise', 'Soumise'), ('validee', 'Validée'), ('rejetee', 'Rejetée')]
    contribuable = models.ForeignKey(Contribuable, on_delete=models.CASCADE, related_name='declarations')
    impot = models.ForeignKey(Impot, on_delete=models.CASCADE, related_name='declarations')
    periode = models.CharField(max_length=50)
    montant_declare = models.DecimalField(max_digits=15, decimal_places=2)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='brouillon')
    date_soumission = models.DateTimeField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Déclaration {self.contribuable.nom} - {self.periode}"

    class Meta:
        ordering = ['-date_creation']

class Paiement(models.Model):
    MODE_CHOICES = [('especes', 'Espèces'), ('virement', 'Virement'), ('cheque', 'Chèque'), ('mobile', 'Mobile Money')]
    impot = models.ForeignKey(Impot, on_delete=models.CASCADE, related_name='paiements')
    montant_paye = models.DecimalField(max_digits=15, decimal_places=2)
    mode_paiement = models.CharField(max_length=20, choices=MODE_CHOICES)
    reference = models.CharField(max_length=100, unique=True)
    date_paiement = models.DateTimeField(auto_now_add=True)
    commentaire = models.TextField(blank=True)

    def __str__(self):
        return f"Paiement {self.reference} - {self.montant_paye} FCFA"

    class Meta:
        ordering = ['-date_paiement']

class Penalite(models.Model):
    impot = models.ForeignKey(Impot, on_delete=models.CASCADE, related_name='penalites')
    montant = models.DecimalField(max_digits=15, decimal_places=2)
    motif = models.TextField()
    date_application = models.DateTimeField(auto_now_add=True)
    est_payee = models.BooleanField(default=False)

    def __str__(self):
        return f"Pénalité {self.impot.contribuable.nom} - {self.montant} FCFA"

    class Meta:
        ordering = ['-date_application']

class Notification(models.Model):
    TYPE_CHOICES = [('paiement', 'Paiement'), ('declaration', 'Déclaration'), ('penalite', 'Pénalité'), ('rappel', 'Rappel')]
    contribuable = models.ForeignKey(Contribuable, on_delete=models.CASCADE, related_name='notifications')
    type_notification = models.CharField(max_length=20, choices=TYPE_CHOICES)
    sujet = models.CharField(max_length=200)
    message = models.TextField()
    email_envoye = models.BooleanField(default=False)
    date_envoi = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type_notification} - {self.contribuable.nom}"

    class Meta:
        ordering = ['-date_envoi']