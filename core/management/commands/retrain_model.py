from django.core.management.base import BaseCommand
from core.models import DefaultRiskPredictor

class Command(BaseCommand):
    help = 'Retrain the Random Forest default risk model'

    def handle(self, *args, **options):
        result = DefaultRiskPredictor.train_model()
        self.stdout.write(self.style.SUCCESS(result))