import os
import logging
import json
import re
import time
import requests
from typing import Dict, List, Optional
from datetime import datetime
from urllib.parse import quote_plus

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler
)
from telegram.constants import ParseMode
from telegram.error import TimedOut

# Configuración
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "8557185127:AAFumnURmqstIsWFogqLmbAzHDxD-lNSQ7w"

class Translator:
    """Traductor simple usando APIs públicas gratuitas"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def translate_text(self, text: str, target_lang: str = "es") -> str:
        """Traducir texto usando múltiples APIs gratuitas"""
        if not text or len(text) < 10:
            return text
        
        # Si el texto ya parece estar en español, no traducir
        if self._is_spanish(text):
            return text
        
        try:
            # Método 1: MyMemory API (más confiable)
            translated = self._translate_mymemory(text, target_lang)
            if translated and len(translated) > 10:
                return translated
            
            # Método 2: Libretranslate (API abierta)
            translated = self._translate_libretranslate(text, target_lang)
            if translated and len(translated) > 10:
                return translated
            
            # Método 3: Traducción simple por palabras comunes
            translated = self._simple_translation(text)
            if translated and len(translated) > 10:
                return translated
            
        except Exception as e:
            print(f"Error en traducción: {e}")
        
        return text  # Si todo falla, devolver texto original
    
    def _translate_mymemory(self, text: str, target_lang: str) -> Optional[str]:
        """Usar MyMemory Translation API"""
        try:
            url = "https://api.mymemory.translated.net/get"
            params = {
                'q': text[:1000],
                'langpair': f'en|{target_lang}',
                'de': 'telegram_bot@medication.com'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('responseStatus') == 200:
                    translated = data['responseData']['translatedText']
                    return self._clean_translation(translated)
        
        except Exception as e:
            print(f"MyMemory error: {e}")
        
        return None
    
    def _translate_libretranslate(self, text: str, target_lang: str) -> Optional[str]:
        """Usar LibreTranslate API"""
        try:
            # Probar diferentes servidores de LibreTranslate
            servers = [
                'https://libretranslate.com',
                'https://translate.argosopentech.com',
                'https://libretranslate.de'
            ]
            
            for server in servers:
                try:
                    url = f"{server}/translate"
                    data = {
                        'q': text[:1000],
                        'source': 'en',
                        'target': target_lang,
                        'format': 'text'
                    }
                    
                    response = self.session.post(url, json=data, timeout=10)
                    if response.status_code == 200:
                        result = response.json()
                        if 'translatedText' in result:
                            translated = result['translatedText']
                            return self._clean_translation(translated)
                
                except Exception:
                    continue  # Intentar con siguiente servidor
        
        except Exception as e:
            print(f"LibreTranslate error: {e}")
        
        return None
    
    def _simple_translation(self, text: str) -> str:
        """Traducción simple de términos médicos comunes"""
        # Diccionario de términos médicos comunes
        medical_terms = {
            'headache': 'dolor de cabeza',
            'fever': 'fiebre',
            'pain': 'dolor',
            'infection': 'infección',
            'inflammation': 'inflamación',
            'swelling': 'hinchazón',
            'nausea': 'náuseas',
            'vomiting': 'vómito',
            'diarrhea': 'diarrea',
            'constipation': 'estreñimiento',
            'take': 'tomar',
            'use': 'usar',
            'apply': 'aplicar',
            'administer': 'administrar',
            'dose': 'dosis',
            'dosage': 'posología',
            'daily': 'diariamente',
            'weekly': 'semanalmente',
            'monthly': 'mensualmente',
            'tablet': 'tableta',
            'capsule': 'cápsula',
            'pill': 'pastilla',
            'injection': 'inyección',
            'cream': 'crema',
            'ointment': 'ungüento',
            'syrup': 'jarabe',
            'drops': 'gotas',
            'warning': 'advertencia',
            'caution': 'precaución',
            'danger': 'peligro',
            'side effect': 'efecto secundario',
            'contraindication': 'contraindicación',
            'interaction': 'interacción',
            'allergy': 'alergia',
            'overdose': 'sobredosis',
            'before meals': 'antes de las comidas',
            'after meals': 'después de las comidas',
            'with food': 'con alimentos',
            'on empty stomach': 'en ayunas',
            'morning': 'mañana',
            'evening': 'tarde',
            'night': 'noche',
            'bedtime': 'hora de acostarse'
        }
        
        # Traducir palabras comunes
        translated_text = text
        for eng, esp in medical_terms.items():
            pattern = r'\b' + re.escape(eng) + r'\b'
            translated_text = re.sub(pattern, esp, translated_text, flags=re.IGNORECASE)
        
        return translated_text if translated_text != text else text
    
    def _is_spanish(self, text: str) -> bool:
        """Detectar si el texto ya está en español"""
        spanish_words = ['el', 'la', 'los', 'las', 'de', 'que', 'y', 'en', 'un', 'una', 'con', 'por', 'para', 'es', 'son', 'del', 'se']
        
        words = text.lower().split()
        spanish_count = sum(1 for word in words if word in spanish_words)
        
        if len(words) > 0:
            return (spanish_count / len(words)) > 0.15
        return False
    
    def _clean_translation(self, text: str) -> str:
        """Limpiar texto traducido"""
        if not text:
            return text
        
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'\(.*?\)', '', text)
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text

class SmartMedicationFinder:
    """Encuentra información usando APIs públicas"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.translator = Translator()
    
    def search_medication(self, name: str) -> Dict:
        """Buscar usando múltiples métodos"""
        results = {}
        normalized_name = self.normalize_name(name)
        
        print(f"🔍 Buscando: {normalized_name}")
        
        # Método 1: Wikipedia API
        wiki_result = self.wikipedia_search(normalized_name)
        if wiki_result:
            results['Wikipedia'] = wiki_result
            print("✅ Wikipedia encontrado")
        
        # Método 2: MedlinePlus API
        medline_result = self.medlineplus_search(normalized_name)
        if medline_result:
            results['MedlinePlus'] = medline_result
            print("✅ MedlinePlus encontrado")
        
        # Método 3: OpenFDA API
        fda_result = self.openfda_search(normalized_name)
        if fda_result:
            results['FDA'] = fda_result
            print("✅ FDA encontrado")
        
        # Método 4: DuckDuckGo API
        if len(results) < 2:
            ddg_result = self.duckduckgo_search(normalized_name)
            if ddg_result:
                results['DuckDuckGo'] = ddg_result
                print("✅ DuckDuckGo encontrado")
        
        # Traducir información al español
        results = self._translate_results(results)
        
        return results
    
    def _translate_results(self, results: Dict) -> Dict:
        """Traducir resultados al español"""
        if not results:
            return results
        
        translated_results = {}
        for fuente, data in results.items():
            if not data:
                translated_results[fuente] = data
                continue
            
            translated_data = data.copy()
            
            fields_to_translate = ['descripcion', 'description', 'indicaciones', 
                                 'dosis', 'efectos_secundarios', 'contraindicaciones',
                                 'precauciones', 'interacciones', 'abstract', 'content']
            
            for field in fields_to_translate:
                if field in translated_data and isinstance(translated_data[field], str):
                    if (not self.translator._is_spanish(translated_data[field]) and 
                        len(translated_data[field]) > 30):
                        try:
                            translated = self.translator.translate_text(
                                translated_data[field], 
                                target_lang="es"
                            )
                            if translated and len(translated) > 30:
                                translated_data[field] = translated
                        except Exception as e:
                            print(f"Error traduciendo campo {field}: {e}")
            
            translated_fields = [f for f in fields_to_translate 
                               if f in data and f in translated_data 
                               and data[f] != translated_data[f]]
            
            if translated_fields:
                translated_data['traducido'] = True
            
            translated_results[fuente] = translated_data
        
        return translated_results
    
    def wikipedia_search(self, medicamento: str) -> Optional[Dict]:
        """Buscar en Wikipedia API"""
        try:
            # Primero buscar en español
            search_url = "https://es.wikipedia.org/w/api.php"
            params = {
                'action': 'query',
                'format': 'json',
                'list': 'search',
                'srsearch': f'{medicamento} medicamento',
                'utf8': 1,
                'srlimit': 1
            }
            
            response = self.session.get(search_url, params=params, timeout=8)
            if response.status_code == 200:
                data = response.json()
                
                if data['query']['search']:
                    page_title = data['query']['search'][0]['title']
                    
                    content_url = "https://es.wikipedia.org/w/api.php"
                    content_params = {
                        'action': 'query',
                        'format': 'json',
                        'titles': page_title,
                        'prop': 'extracts',
                        'exintro': True,
                        'explaintext': True,
                        'utf8': 1
                    }
                    
                    content_response = self.session.get(content_url, params=content_params, timeout=8)
                    if content_response.status_code == 200:
                        content_data = content_response.json()
                        pages = content_data['query']['pages']
                        page_id = list(pages.keys())[0]
                        page_content = pages[page_id].get('extract', '')
                        
                        if page_content and len(page_content) > 50:
                            return {
                                'nombre': page_title,
                                'descripcion': page_content[:600] + "..." if len(page_content) > 600 else page_content,
                                'url': f"https://es.wikipedia.org/wiki/{quote_plus(page_title)}",
                                'fuente': 'Wikipedia Español'
                            }
            
            # Si no encuentra en español, buscar en inglés
            search_url_en = "https://en.wikipedia.org/w/api.php"
            params_en = {
                'action': 'query',
                'format': 'json',
                'list': 'search',
                'srsearch': f'{medicamento} drug',
                'utf8': 1,
                'srlimit': 1
            }
            
            response_en = self.session.get(search_url_en, params=params_en, timeout=8)
            if response_en.status_code == 200:
                data_en = response_en.json()
                
                if data_en['query']['search']:
                    page_title_en = data_en['query']['search'][0]['title']
                    
                    content_url_en = "https://en.wikipedia.org/w/api.php"
                    content_params_en = {
                        'action': 'query',
                        'format': 'json',
                        'titles': page_title_en,
                        'prop': 'extracts',
                        'exintro': True,
                        'explaintext': True,
                        'utf8': 1
                    }
                    
                    content_response_en = self.session.get(content_url_en, params=content_params_en, timeout=8)
                    if content_response_en.status_code == 200:
                        content_data_en = content_response_en.json()
                        pages_en = content_data_en['query']['pages']
                        page_id_en = list(pages_en.keys())[0]
                        page_content_en = pages_en[page_id_en].get('extract', '')
                        
                        if page_content_en and len(page_content_en) > 100:
                            return {
                                'nombre': page_title_en,
                                'descripcion': page_content_en[:600] + "..." if len(page_content_en) > 600 else page_content_en,
                                'url': f"https://en.wikipedia.org/wiki/{quote_plus(page_title_en)}",
                                'fuente': 'Wikipedia English'
                            }
                    else:
                        return {
                            'nombre': page_title_en,
                            'descripcion': f'Información disponible en Wikipedia en inglés.',
                            'url': f"https://en.wikipedia.org/wiki/{quote_plus(page_title_en)}",
                            'fuente': 'Wikipedia English'
                        }
                        
        except Exception as e:
            print(f"Wikipedia error: {e}")
        
        return None
    
    def medlineplus_search(self, medicamento: str) -> Optional[Dict]:
        """Buscar en MedlinePlus API"""
        try:
            search_url = "https://medlineplus.gov/medlineplus-rest/v2/search"
            params = {
                'q': f'{medicamento}',
                'lang': 'es',
                'maxDocs': 1
            }
            
            response = self.session.get(search_url, params=params, timeout=8)
            if response.status_code == 200:
                data = response.json()
                
                if data.get('total') > 0 and data.get('results'):
                    result = data['results'][0]
                    
                    detail_url = f"https://medlineplus.gov/medlineplus-rest/v2/drug/{result['id']}"
                    detail_response = self.session.get(detail_url, timeout=8)
                    
                    if detail_response.status_code == 200:
                        detail_data = detail_response.json()
                        
                        info = {
                            'nombre': detail_data.get('title', medicamento.title()),
                            'descripcion': detail_data.get('description', ''),
                            'url': f"https://medlineplus.gov/spanish/druginfo/{result['id']}.html",
                            'fuente': 'MedlinePlus (NIH)'
                        }
                        
                        if 'sections' in detail_data:
                            for section in detail_data['sections']:
                                if section.get('title') and section.get('content'):
                                    key = section['title'].lower().replace(' ', '_')
                                    content = section['content']
                                    if len(content) > 400:
                                        content = content[:400] + "..."
                                    info[key] = content
                        
                        return info
                        
        except Exception as e:
            print(f"MedlinePlus error: {e}")
        
        return None
    
    def openfda_search(self, medicamento: str) -> Optional[Dict]:
        """Buscar en OpenFDA API"""
        try:
            search_url = "https://api.fda.gov/drug/label.json"
            params = {
                'search': f'openfda.generic_name:"{medicamento}" OR openfda.brand_name:"{medicamento}"',
                'limit': 1
            }
            
            response = self.session.get(search_url, params=params, timeout=8)
            if response.status_code == 200:
                data = response.json()
                
                if data.get('results') and len(data['results']) > 0:
                    drug_info = data['results'][0]
                    
                    nombre = medicamento.title()
                    if 'openfda' in drug_info and 'generic_name' in drug_info['openfda']:
                        nombre = drug_info['openfda']['generic_name'][0]
                    elif 'openfda' in drug_info and 'brand_name' in drug_info['openfda']:
                        nombre = drug_info['openfda']['brand_name'][0]
                    
                    info = {
                        'nombre': nombre,
                        'fuente': 'FDA (USA)',
                        'url': 'https://www.accessdata.fda.gov'
                    }
                    
                    fields_to_extract = {
                        'descripcion': 'description',
                        'indicaciones': 'indications_and_usage',
                        'dosis': 'dosage_and_administration',
                        'efectos_secundarios': 'adverse_reactions',
                        'contraindicaciones': 'contraindications',
                        'precauciones': 'warnings',
                        'interacciones': 'drug_interactions'
                    }
                    
                    for esp_key, eng_key in fields_to_extract.items():
                        if eng_key in drug_info:
                            value = drug_info[eng_key]
                            if isinstance(value, list):
                                combined = ' '.join(value[:2])
                                if len(combined) > 400:
                                    combined = combined[:400] + "..."
                                info[esp_key] = combined
                            elif isinstance(value, str):
                                if len(value) > 400:
                                    value = value[:400] + "..."
                                info[esp_key] = value
                    
                    if 'openfda' in drug_info:
                        openfda_info = drug_info['openfda']
                        if 'route' in openfda_info:
                            info['via_administracion'] = ', '.join(openfda_info['route'][:2])
                        if 'substance_name' in openfda_info:
                            info['sustancia_activa'] = ', '.join(openfda_info['substance_name'][:2])
                    
                    return info if len(info) > 3 else None
                        
        except Exception as e:
            print(f"OpenFDA error: {e}")
        
        return None
    
    def duckduckgo_search(self, medicamento: str) -> Optional[Dict]:
        """Buscar en DuckDuckGo Instant Answer API"""
        try:
            search_url = "https://api.duckduckgo.com/"
            params = {
                'q': f'{medicamento} medicamento',
                'format': 'json',
                'no_html': 1,
                'skip_disambig': 1,
                't': 'telegram_bot'
            }
            
            response = self.session.get(search_url, params=params, timeout=8)
            if response.status_code == 200:
                data = response.json()
                
                info = {
                    'nombre': data.get('Heading', medicamento.title()),
                    'fuente': 'DuckDuckGo'
                }
                
                if data.get('AbstractText'):
                    abstract = data['AbstractText']
                    if len(abstract) > 400:
                        abstract = abstract[:400] + "..."
                    info['descripcion'] = abstract
                
                if data.get('AbstractURL'):
                    info['url'] = data['AbstractURL']
                
                return info if 'descripcion' in info else None
                        
        except Exception as e:
            print(f"DuckDuckGo error: {e}")
        
        return None
    
    def normalize_name(self, name: str) -> str:
        """Normalizar nombre del medicamento"""
        name = name.lower().strip()
        
        translations = {
            'aspirina': 'aspirin',
            'ibuprofeno': 'ibuprofen',
            'paracetamol': 'acetaminophen',
            'omeprazol': 'omeprazole',
            'amoxicilina': 'amoxicillin',
            'metformina': 'metformin',
            'atorvastatina': 'atorvastatin',
            'simvastatina': 'simvastatin',
            'losartan': 'losartan',
            'enalapril': 'enalapril',
            'diazepam': 'diazepam',
            'lorazepam': 'lorazepam',
            'warfarin': 'warfarin',
            'insulina': 'insulin',
            'prednisona': 'prednisone',
            'hidroclorotiazida': 'hydrochlorothiazide',
        }
        
        if name in translations:
            return translations[name]
        
        return name

class MedicationFormatter:
    """Formatea la información para Telegram"""
    
    def __init__(self):
        self.translator = Translator()
    
    def format_results(self, search_results: Dict, query: str) -> str:
        """Formatear resultados de búsqueda"""
        if not search_results:
            return self._format_no_results(query)
        
        message_parts = []
        
        nombre = self._get_best_name(search_results, query)
        message_parts.append(f"💊 *{nombre.upper()}*")
        message_parts.append("")
        
        fuentes = list(search_results.keys())
        if fuentes:
            message_parts.append(f"📚 *Fuentes:* {', '.join(fuentes)}")
            message_parts.append("")
        
        has_translation = any(data.get('traducido', False) for data in search_results.values() if data)
        if has_translation:
            message_parts.append("🌐 *Traducido automáticamente*")
            message_parts.append("")
        
        categorized_info = self._categorize_info(search_results)
        
        categories_to_show = [
            ('descripcion', '📄 Descripción'),
            ('indicaciones', '🎯 Indicaciones'),
            ('dosis', '💊 Dosis'),
            ('efectos_secundarios', '⚠️ Efectos secundarios'),
            ('contraindicaciones', '🚫 Contraindicaciones'),
            ('precauciones', '📝 Precauciones'),
            ('interacciones', '🔀 Interacciones'),
            ('via_administracion', '🔄 Vía de administración'),
            ('sustancia_activa', '🧪 Sustancia activa')
        ]
        
        for cat_key, cat_title in categories_to_show:
            if cat_key in categorized_info and categorized_info[cat_key]:
                items = categorized_info[cat_key]
                
                message_parts.append(f"*{cat_title}:*")
                
                shown_sources = set()
                for item in items:
                    fuente = item.get('fuente', '')
                    texto = item.get('texto', '')
                    
                    if fuente not in shown_sources and texto:
                        if not self.translator._is_spanish(texto):
                            texto = self.translator.translate_text(texto, "es")
                        
                        texto_clean = self._clean_text(texto, 250)
                        message_parts.append(f"• {texto_clean}")
                        if fuente:
                            message_parts.append(f"  └─ {fuente}")
                        
                        shown_sources.add(fuente)
                        if len(shown_sources) >= 2:
                            break
                
                message_parts.append("")
        
        urls = self._extract_urls(search_results)
        if urls:
            message_parts.append("*🔗 Más información:*")
            for url_info in urls[:3]:
                message_parts.append(f"• [{url_info['fuente']}]({url_info['url']})")
            message_parts.append("")
        
        message_parts.append("═" * 35)
        message_parts.append("📋 *IMPORTANTE:*")
        
        if has_translation:
            message_parts.append("• ✅ Traducido automáticamente")
        
        message_parts.append("• ℹ️ APIs públicas oficiales")
        message_parts.append("• ⚠️ Consulte con un profesional")
        message_parts.append(f"• 📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        
        final_message = "\n".join(message_parts)
        if len(final_message) > 4000:
            final_message = final_message[:3900] + "\n\n... (mensaje muy largo)"
        
        return final_message
    
    @staticmethod
    def _get_best_name(results: Dict, query: str) -> str:
        """Obtener el mejor nombre"""
        for data in results.values():
            if data and data.get('nombre'):
                return data['nombre']
        return query.title()
    
    def _categorize_info(self, results: Dict) -> Dict:
        """Categorizar información por tipo"""
        categorized = {}
        
        field_mapping = {
            'descripcion': ['descripcion', 'description', 'abstract', 'resumen'],
            'indicaciones': ['indicaciones', 'indications', 'usos', 'indications_and_usage'],
            'dosis': ['dosis', 'dosage', 'posologia', 'dosage_and_administration'],
            'efectos_secundarios': ['efectos_secundarios', 'side_effects', 'adverse_reactions'],
            'contraindicaciones': ['contraindicaciones', 'contraindications'],
            'precauciones': ['precauciones', 'warnings', 'precautions'],
            'interacciones': ['interacciones', 'interactions', 'drug_interactions'],
            'via_administracion': ['via_administracion', 'route'],
            'sustancia_activa': ['sustancia_activa', 'substance_name', 'generic_name']
        }
        
        for fuente, data in results.items():
            if not data:
                continue
            
            for cat_key, field_names in field_mapping.items():
                for field in field_names:
                    if field in data and data[field]:
                        if cat_key not in categorized:
                            categorized[cat_key] = []
                        
                        texto = data[field]
                        if isinstance(texto, str) and len(texto) > 20:
                            categorized[cat_key].append({
                                'fuente': fuente,
                                'texto': texto
                            })
                        break
        
        return categorized
    
    @staticmethod
    def _clean_text(text: str, max_len: int = 250) -> str:
        """Limpiar y truncar texto"""
        if not text:
            return ""
        
        text = re.sub(r'\s+', ' ', text).strip()
        
        if len(text) > max_len:
            last_dot = text.rfind('.', 0, max_len)
            last_comma = text.rfind(',', 0, max_len)
            
            if last_dot > max_len * 0.5:
                return text[:last_dot + 1]
            elif last_comma > max_len * 0.5:
                return text[:last_comma] + "..."
            else:
                return text[:max_len] + "..."
        
        return text
    
    @staticmethod
    def _extract_urls(results: Dict) -> List[Dict]:
        """Extraer URLs"""
        urls = []
        for fuente, data in results.items():
            if data and data.get('url'):
                urls.append({
                    'fuente': fuente,
                    'url': data['url']
                })
        return urls
    
    @staticmethod
    def _format_no_results(query: str) -> str:
        """Formatear cuando no hay resultados"""
        return (
            f"❌ *No se encontró información para:* `{query}`\n\n"
            "💡 *Prueba con:*\n"
            "• `aspirin` (aspirina)\n"
            "• `ibuprofen` (ibuprofeno)\n"
            "• `acetaminophen` (paracetamol)\n"
            "• `omeprazole` (omeprazol)\n\n"
            "⚠️ *Nota:* Usa nombres en inglés para mejores resultados."
        )

class WorkingMedicationBot:
    """Bot de medicamentos"""
    
    def __init__(self):
        self.finder = SmartMedicationFinder()
        self.formatter = MedicationFormatter()
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start"""
        keyboard = [
            [InlineKeyboardButton("💊 Buscar", callback_data="search")],
            [InlineKeyboardButton("📚 Ejemplos", callback_data="examples")],
            [InlineKeyboardButton("ℹ️ Ayuda", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🏥 *Bot de Medicamentos*\n\n"
            "*✅ Funciona con APIs públicas:*\n"
            "• Wikipedia API\n"
            "• MedlinePlus API\n"
            "• FDA API\n"
            "• 🌐 Traducción automática\n\n"
            "*💊 Escribe un medicamento:*\n\n"
            "*En inglés (recomendado):*\n"
            "`aspirin` `ibuprofen` `omeprazole`\n\n"
            "*En español:*\n"
            "`paracetamol` `diazepam` `warfarin`",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def search_medication(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Buscar medicamento"""
        query = update.message.text.strip()
        
        if not query or len(query) < 3:
            await update.message.reply_text(
                "❌ Escribe al menos 3 letras.\nEjemplo: `aspirin`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        processing_msg = await update.message.reply_text(
            f"🔍 *Buscando:* `{query}`\n"
            "🔄 Consultando APIs...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            search_results = self.finder.search_medication(query)
            formatted_message = self.formatter.format_results(search_results, query)
            
            await processing_msg.edit_text(
                formatted_message,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            
        except Exception as e:
            print(f"Error: {e}")
            await processing_msg.edit_text(
                f"❌ *Error al buscar:* `{query}`\n\n"
                "💡 *Prueba con:*\n"
                "• `aspirin`\n"
                "• `ibuprofen`\n"
                "• `acetaminophen`\n"
                "• `omeprazole`",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /help"""
        help_text = (
            "🆘 *AYUDA*\n\n"
            "*APIs usadas:*\n"
            "✅ Wikipedia API\n"
            "✅ MedlinePlus API\n"
            "✅ FDA API\n"
            "✅ DuckDuckGo API\n"
            "✅ Traducción automática\n\n"
            "*Ejemplos:*\n"
            "• `aspirin`\n"
            "• `ibuprofen`\n"
            "• `omeprazole`\n"
            "• `acetaminophen`\n\n"
            "*Info que obtienes:*\n"
            "• Descripción\n"
            "• Indicaciones\n"
            "• Dosis\n"
            "• Efectos secundarios\n"
            "• Contraindicaciones\n"
            "• Precauciones\n\n"
            "⚠️ *Solo para información.*"
        )
        
        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def buscar_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /buscar"""
        if not context.args:
            await update.message.reply_text(
                "🔍 *Uso:* /buscar [nombre]\n\n"
                "*Ejemplos:*\n"
                "`/buscar aspirin`\n"
                "`/buscar ibuprofen`\n"
                "`/buscar acetaminophen`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        query = ' '.join(context.args)
        await self.search_medication(update, context)
    
    async def ejemplos_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /ejemplos"""
        ejemplos_text = (
            "💊 *EJEMPLOS:*\n\n"
            "*En inglés:*\n"
            "• `aspirin` - Ácido acetilsalicílico\n"
            "• `ibuprofen` - Ibuprofeno\n"
            "• `omeprazole` - Omeprazol\n"
            "• `amoxicillin` - Amoxicilina\n"
            "• `metformin` - Metformina\n\n"
            "*En español:*\n"
            "• `paracetamol` - Paracetamol\n"
            "• `diazepam` - Diazepam\n"
            "• `warfarin` - Warfarina\n\n"
            "💡 *Usa inglés para más información.*"
        )
        
        await update.message.reply_text(
            ejemplos_text,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejador de botones"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "search":
            await query.edit_message_text(
                "🔍 *Escribe un medicamento:*\n\n"
                "*Ejemplos:*\n"
                "`aspirin`\n"
                "`ibuprofen`\n"
                "`omeprazole`\n"
                "`acetaminophen`",
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif query.data == "examples":
            await query.edit_message_text(
                "💊 *Ejemplos:*\n\n"
                "*En inglés:*\n"
                "• `aspirin`\n"
                "• `ibuprofen`\n"
                "• `omeprazole`\n\n"
                "*En español:*\n"
                "• `paracetamol`\n"
                "• `diazepam`\n"
                "• `warfarin`",
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif query.data == "help":
            await query.edit_message_text(
                "ℹ️ *Ayuda rápida:*\n\n"
                "*Escribe en inglés:*\n"
                "`aspirin` `ibuprofen` `omeprazole`\n\n"
                "*Algunos en español:*\n"
                "`paracetamol` `diazepam` `warfarin`\n\n"
                "*Se traduce automáticamente*",
                parse_mode=ParseMode.MARKDOWN
            )

async def post_init(application: Application) -> None:
    """Función que se ejecuta después de inicializar"""
    print("=" * 50)
    print("✅ Bot iniciado correctamente")
    print("💊 Prueba con: aspirin, ibuprofen, omeprazole")
    print("🌐 La información se traduce automáticamente")
    print("=" * 50)

def main():
    """Función principal con manejo de errores mejorado"""
    try:
                # Crear aplicación con configuración para evitar timeouts
        application = Application.builder() \
            .token(TOKEN) \
            .connect_timeout(30.0) \
            .read_timeout(30.0) \
            .write_timeout(30.0) \
            .pool_timeout(30.0) \
            .build()
        
        # Crear instancia del bot
        bot = WorkingMedicationBot()
        
        # Comandos
        application.add_handler(CommandHandler("start", bot.start))
        application.add_handler(CommandHandler("help", bot.help_command))
        application.add_handler(CommandHandler("buscar", bot.buscar_command))
        application.add_handler(CommandHandler("ejemplos", bot.ejemplos_command))
        
        # Manejador de mensajes
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            bot.search_medication
        ))
        
        # Manejador de botones
        application.add_handler(CallbackQueryHandler(bot.button_handler))
        
        print("=" * 50)
        print("🤖 INICIANDO BOT DE MEDICAMENTOS...")
        print("=" * 50)
        print("📱 Token: " + TOKEN[:10] + "..." + TOKEN[-10:])
        print("💊 Prueba con: aspirin, ibuprofen, omeprazole")
        print("🌐 Traducción automática activada")
        print("⏱️ Timeouts configurados: 30 segundos")
        print("=" * 50)
        
        # Configurar post_init
        application.post_init = post_init
        
        # Ejecutar con reintentos
        print("🔄 Conectando con Telegram...")
        
        # Intentar conectar con reintentos
        max_retries = 3
        for retry in range(max_retries):
            try:
                print(f"Intento {retry + 1} de {max_retries}...")
                application.run_polling(
                    drop_pending_updates=True,
                    allowed_updates=Update.ALL_TYPES,
                    close_loop=False)
                break  # Si funciona, salir del bucle
            except TimedOut as e:
                print(f"⚠️ Timeout en intento {retry + 1}: {e}")
                if retry < max_retries - 1:
                    wait_time = 5 * (retry + 1)
                    print(f"⏳ Esperando {wait_time} segundos antes de reintentar...")
                    time.sleep(wait_time)
                else:
                    print("❌ No se pudo conectar después de varios intentos")
                    raise
            except Exception as e:
                print(f"❌ Error inesperado: {e}")
                raise
        
    except KeyboardInterrupt:
        print("\n🛑 Bot detenido por el usuario")
    except Exception as e:
        print(f"\n❌ Error crítico: {e}")
        print("💡 Soluciones posibles:")
        print("1. Verifica tu conexión a internet")
        print("2. Asegúrate de que el token sea correcto")
        print("3. Verifica si hay bloqueos de firewall")
        print("4. Intenta ejecutar en otro momento")
        print("=" * 50)

if __name__ == '__main__':
    # Verificar dependencias
    try:
        import httpx
        import httpcore
        print("✅ Dependencias verificadas")
    except ImportError as e:
        print(f"❌ Faltan dependencias: {e}")
        print("💡 Ejecuta: pip install python-telegram-bot httpx requests")
        exit(1)
    
    # Verificar conexión a internet
    print("🌐 Verificando conexión a internet...")
    try:
        response = requests.get("https://api.telegram.org", timeout=10)
        print("✅ Conexión a Telegram disponible")
    except:
        print("⚠️ No se pudo verificar conexión a Telegram")
        print("💡 Asegúrate de tener conexión a internet")
    
    # Ejecutar main
    print("\n" + "=" * 50)
    print("🚀 INICIANDO BOT...")
    print("=" * 50)
    
    try:
        main()
    except SystemExit:
        print("\n👋 Bot finalizado")
    except Exception as e:
        print(f"\n💥 Error fatal: {e}")
        print("📋 Información para depuración:")
        import traceback
        traceback.print_exc()
        print("=" * 50)
        print("💡 Si el problema persiste:")
        print("1. Verifica que el token sea válido")
        print("2. Intenta reiniciar el bot")
        print("3. Verifica tu conexión a internet")
        print("4. Contacta con soporte si es necesario")