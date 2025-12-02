# Service de Conversion PDF → Word

## Vue d'ensemble

Ce service permet de convertir le rapport annuel de performance (PDF) en document Word (.docx) pour permettre aux utilisateurs de modifier le rapport directement dans Microsoft Word.

## Architecture

### Fichiers créés

1. **`app/services/pdf_to_word_service.py`**
   - Service principal de conversion
   - Utilise Adobe PDF Services SDK
   - Gère les credentials et la configuration

2. **Endpoint API**
   - Ajouté dans `app/api/v1/endpoints/performance.py`
   - Route: `/rapport-annuel-performance/docx-simpledoc`

## Configuration requise

### 1. Installation du SDK Adobe PDF Services

Le SDK doit être installé dans l'environnement Python :

```bash
pip install pdfservices-sdk
```

Ajoutez également cette dépendance à `requirements.txt` si nécessaire.

### 2. Configuration des credentials Adobe

Vous avez deux options pour configurer les credentials :

#### Option A: Variables d'environnement (Recommandé)

Définissez ces variables dans votre fichier `.env` :

```env
PDF_SERVICES_CLIENT_ID=votre_client_id
PDF_SERVICES_CLIENT_SECRET=votre_client_secret
```

#### Option B: Fichier de credentials

Le service cherche automatiquement dans :
- `app/PDFServicesSDK-PythonSamples/pdfservices-api-credentials.json`

Ce fichier contient déjà les credentials fournis avec le SDK :
```json
{
 "client_credentials": {
  "client_id": "679b417139e945e793ff11422725db81",
  "client_secret": "p8e-ywGQmB-6_MkSZZIxLHu7ePyN9OomBDI2"
 },
 "service_principal_credentials": {
  "organization_id": "72751E6466C715870A495FD4@AdobeOrg"
 }
}
```

## Utilisation

### Via l'API

**Endpoint:** `GET /rapport-annuel-performance/docx-simpledoc`

**Paramètres de requête (identiques à l'endpoint PDF) :**
- `annee`: Année du rapport
- `mode`: Mode de génération (`brouillon` ou `final`)
- `ocr`: Activer OCR pour extraire le texte des images (`true` ou `false`, par défaut `false`)

**Exemple d'utilisation :**

```javascript
// Dans le frontend
fetch('/api/v1/rapport-annuel-performance/docx-simpledoc?annee=2024&mode=final&ocr=false')
  .then(response => response.blob())
  .then(blob => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'rapport_annuel_performance_2024_final.docx';
    a.click();
  });
```

### Via le code Python

```python
from app.services.pdf_to_word_service import PDFToWordService
from io import BytesIO

# Générer le PDF d'abord (via RAPPDFGenerator)
pdf_buffer = RAPPDFGenerator.generate_pdf(data, session=db)

# Convertir en Word
word_buffer = PDFToWordService.convert_pdf_to_word(
    pdf_buffer, 
    use_ocr=False  # True pour activer OCR sur les images
)

# Sauvegarder ou retourner le document Word
with open('rapport.docx', 'wb') as f:
    word_buffer.seek(0)
    f.write(word_buffer.read())
```

## Fonctionnalités

### Conversion standard
- Conversion PDF → Word avec préservation de la structure
- Mise en page préservée
- Textes et tableaux conservés

### OCR (Optical Character Recognition)
- Activez avec `ocr=true` ou `use_ocr=True`
- Extrait le texte des images dans le PDF
- Utile pour les PDFs scannés ou avec beaucoup d'images
- Langue par défaut: Français (`FR_FR`)

## Gestion des erreurs

Le service gère plusieurs types d'erreurs :

1. **Credentials manquants**
   - Message: "Les credentials Adobe PDF Services ne sont pas configurés"
   - Solution: Configurez les variables d'environnement ou le fichier de credentials

2. **SDK non installé**
   - Message: "Le SDK Adobe PDF Services n'est pas installé"
   - Solution: `pip install pdfservices-sdk`

3. **Erreurs Adobe PDF Services**
   - Messages détaillés selon le type d'erreur
   - Vérifiez les quotas d'utilisation Adobe

## Limitations et notes importantes

1. **Quota Adobe**
   - Les credentials de test ont un quota limité
   - Pour la production, obtenez des credentials payants auprès d'Adobe

2. **Performance**
   - La conversion peut prendre plusieurs secondes selon la taille du PDF
   - Le PDF est uploadé sur Adobe Cloud pendant la conversion

3. **Qualité de conversion**
   - La qualité dépend de la complexité du PDF original
   - Les graphiques complexes peuvent nécessiter des ajustements manuels dans Word

4. **Format de sortie**
   - Format: `.docx` (Word 2007+)
   - Compatible avec Microsoft Word, LibreOffice, Google Docs

## Intégration dans le frontend

Pour ajouter un bouton de téléchargement Word dans l'interface :

```html
<button onclick="downloadAsWord()" class="btn btn-primary">
    📄 Télécharger en Word
</button>

<script>
function downloadAsWord() {
    const year = document.getElementById('annee').value;
    const mode = document.getElementById('mode').value;
    const url = `/api/v1/rapport-annuel-performance/docx-simpledoc?annee=${year}&mode=${mode}`;
    
    window.location.href = url; // Téléchargement direct
}
</script>
```

## Support et dépannage

### Vérifier que le SDK est installé

```python
python -c "import adobe.pdfservices.operation; print('SDK installé')"
```

### Vérifier les credentials

```python
from app.services.pdf_to_word_service import PDFToWordService
client_id, client_secret = PDFToWordService._load_credentials()
print(f"Client ID: {client_id is not None}, Client Secret: {client_secret is not None}")
```

### Logs

Les logs détaillent chaque étape de la conversion :
- `🔄 Début de la conversion PDF → Word`
- `✅ PDF téléchargé sur Adobe Cloud`
- `⏳ Envoi du job de conversion...`
- `✅ Conversion PDF → Word terminée avec succès`

Consultez les logs de l'application pour diagnostiquer les problèmes.

