from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from painel.models import RegistroCotacao


class Command(BaseCommand):
    help = 'Consulta e registra automaticamente as cotações.'

    def handle(self, *args, **options):
        try:
            resposta = requests.get(
                settings.COTACOES_MULTIPLAS_URL,
                timeout=5
            )
            resposta.raise_for_status()
            dados = resposta.json()

            registros = []

            for moeda in ['USD', 'EUR', 'BTC']:
                valor = Decimal(dados[f'{moeda}BRL']['bid'])

                if not valor.is_finite() or valor <= 0:
                    raise ValueError('Cotação inválida.')

                registros.append(
                    RegistroCotacao(
                        moeda_origem=moeda,
                        moeda_destino='BRL',
                        valor=valor
                    )
                )

        except (
            requests.exceptions.RequestException,
            ValueError,
            KeyError,
            TypeError,
            InvalidOperation
        ) as erro:
            raise CommandError(
                f'Não foi possível consultar as cotações: {erro}'
            ) from erro

        RegistroCotacao.objects.bulk_create(registros)

        self.stdout.write(
            self.style.SUCCESS(
                'Cotações de USD, EUR e BTC registradas com sucesso!'
            )
        )
