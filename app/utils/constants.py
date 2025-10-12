"""
Constantes de l'application
"""

# ==========================================
# AUTHENTIFICATION
# ==========================================

# Mot de passe
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
PASSWORD_REGEX = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$'

# Email
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
EMAIL_MAX_LENGTH = 255

# Sécurité
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15
SESSION_TIMEOUT_MINUTES = 60
SESSION_TIMEOUT = SESSION_TIMEOUT_MINUTES * 60  # En secondes pour compatibilité

# Codes de vérification
VERIFICATION_CODE_LENGTH = 6
VERIFICATION_CODE_EXPIRY_MINUTES = 15
MAX_VERIFICATION_ATTEMPTS = 5

# ==========================================
# PAGINATION
# ==========================================

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# ==========================================
# FICHIERS
# ==========================================

# Upload
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Extensions autorisées
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
ALLOWED_DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt'}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_DOCUMENT_EXTENSIONS

# ==========================================
# FORMATS
# ==========================================

# Dates
DATE_FORMAT = "%d/%m/%Y"
DATETIME_FORMAT = "%d/%m/%Y %H:%M"
TIME_FORMAT = "%H:%M"
ISO_DATE_FORMAT = "%Y-%m-%d"
ISO_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

# ==========================================
# MESSAGES
# ==========================================

# Messages de succès
MSG_LOGIN_SUCCESS = "Connexion réussie !"
MSG_LOGOUT_SUCCESS = "Déconnexion réussie !"
MSG_REGISTER_SUCCESS = "Compte créé avec succès !"
MSG_PASSWORD_RESET_SUCCESS = "Mot de passe réinitialisé avec succès !"
MSG_EMAIL_SENT = "Email envoyé avec succès !"

# Messages d'erreur
MSG_LOGIN_FAILED = "Email ou mot de passe incorrect"
MSG_ACCOUNT_DISABLED = "Compte désactivé. Contactez l'administrateur."
MSG_ACCOUNT_LOCKED = "Compte verrouillé. Réessayez plus tard."
MSG_EMAIL_ALREADY_EXISTS = "Cet email est déjà utilisé"
MSG_INVALID_TOKEN = "Token invalide ou expiré"
MSG_CODE_INVALID = "Code invalide ou expiré"

# ==========================================
# CODES HTTP
# ==========================================

HTTP_200_OK = 200
HTTP_201_CREATED = 201
HTTP_204_NO_CONTENT = 204
HTTP_400_BAD_REQUEST = 400
HTTP_401_UNAUTHORIZED = 401
HTTP_403_FORBIDDEN = 403
HTTP_404_NOT_FOUND = 404
HTTP_409_CONFLICT = 409
HTTP_422_UNPROCESSABLE_ENTITY = 422
HTTP_500_INTERNAL_SERVER_ERROR = 500

# ==========================================
# RÔLES UTILISATEUR
# ==========================================

ROLE_USER = "user"
ROLE_ADMIN = "admin"
ROLE_SUPERADMIN = "superadmin"

ROLES = [ROLE_USER, ROLE_ADMIN, ROLE_SUPERADMIN]

# ==========================================
# STATUTS
# ==========================================

STATUS_ACTIVE = "active"
STATUS_INACTIVE = "inactive"
STATUS_PENDING = "pending"
STATUS_SUSPENDED = "suspended"

STATUSES = [STATUS_ACTIVE, STATUS_INACTIVE, STATUS_PENDING, STATUS_SUSPENDED]

