from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import render
from rest_framework import generics

from .models import RegistroCotacao
from .serializers import RegistroCotacaoSerializer


def consultar_cotacao(request):
    contexto = {}
    try:
        # timeout evita que a página fique esperando para sempre
        resposta = requests.get(settings.COTACAO_URL, timeout=5)
        resposta.raise_for_status()
        dados = resposta.json()
        valor = Decimal(dados['USDBRL']['bid'])
        registro = RegistroCotacao.objects.create(valor=valor)
        contexto = {'sucesso': True, 'registro': registro}
    except requests.exceptions.RequestException:
        contexto = {'erro': 'Não foi possível consultar a cotação agora. Tente novamente em instantes.'}
    except (ValueError, KeyError, TypeError, InvalidOperation):
        # A API respondeu, mas em um formato inesperado.
        contexto = {'erro': 'A API externa respondeu em um formato inesperado.'}
    return render(request, 'painel/consultar.html', contexto)


class HistoricoCotacaoView(generics.ListAPIView):
    """Somente leitura: histórico do mais recente para o mais antigo."""
    serializer_class = RegistroCotacaoSerializer

    def get_queryset(self):
        return RegistroCotacao.objects.order_by('-data_hora_consulta', '-id')


def consultar_multiplas_cotacoes(request):
    contexto = {}

    try:
        chave_cache = 'cotacoes_multiplas_usd_eur_btc'
        valores = cache.get(chave_cache)

        veio_do_cache = valores is not None

        if valores is None:
            resposta = requests.get(
                settings.COTACOES_MULTIPLAS_URL,
                timeout=5
            )
            resposta.raise_for_status()

            dados = resposta.json()

            valores = {}

            for moeda in ['USD', 'EUR', 'BTC']:
                valores[moeda] = Decimal(
                    dados[f'{moeda}BRL']['bid']
                )

            cache.set(chave_cache, valores, timeout=300)

        registros = []

        for moeda in ['USD', 'EUR', 'BTC']:
            registros.append(
                RegistroCotacao(
                    moeda_origem=moeda,
                    moeda_destino='BRL',
                    valor=valores[moeda]
                )
            )

        RegistroCotacao.objects.bulk_create(registros)

        contexto = {
            'sucesso_multiplas': True,
            'registros': registros,
            'veio_do_cache': veio_do_cache
        }

    except requests.exceptions.RequestException:
        contexto = {
            'erro': 'Não foi possível consultar as cotações agora.'
        }

    except (ValueError, KeyError, TypeError, InvalidOperation):
        contexto = {
            'erro': 'A API externa respondeu em um formato inesperado.'
        }

    return render(request, 'painel/consultar.html', contexto)
