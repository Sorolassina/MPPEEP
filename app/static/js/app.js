// ============================================
// HELPERS GLOBAUX
// ============================================

/**
 * Helper pour préfixer automatiquement les URLs API avec root_path
 * Usage: apiUrl('/api/v1/users') => '/mppeep/api/v1/users' (en prod)
 */
window.apiUrl = window.apiUrl || function(path) {
    // Si le chemin commence déjà par root_path, le retourner tel quel
    if (window.root_path && path.startsWith(window.root_path)) {
        return path;
    }
    // Sinon, ajouter le préfixe
    return window.root_path ? window.root_path + path : path;
};

/**
 * Wrapper de fetch qui préfixe automatiquement les URLs API
 * Remplace le fetch natif pour gérer automatiquement le root_path
 * IMPORTANT: Toujours renvoyer une Response ou jeter l'erreur, jamais undefined
 */
(function() {
    const originalFetch = window.fetch;
    // Exposer originalFetch pour permettre l'utilisation du fetch natif si nécessaire
    window.originalFetch = originalFetch;
    
    window.fetch = async function(url, options) {
        try {
            // Si l'URL est une chaîne et commence par /api/, /static/, ou /uploads/
            if (typeof url === 'string') {
                if (url.startsWith('/api/') || url.startsWith('/static/') || url.startsWith('/uploads/')) {
                    url = window.apiUrl(url);
                }
            }
            
            // Appeler le fetch original avec l'URL préfixée
            const response = await originalFetch(url, options);
            
            // Toujours renvoyer la Response, même si elle n'est pas OK (400, 500, etc.)
            // C'est à l'appelant de vérifier response.ok
            return response;
        } catch (error) {
            // En cas d'erreur réseau (net::ERR_FAILED, etc.), on jette l'erreur
            // On ne retourne JAMAIS undefined silencieusement
            console.error('🔥 [fetch wrapper] Network error:', error);
            throw error;
        }
    };
})();

// ============================================
// FONCTIONS UTILITAIRES
// ============================================

/**
 * Convertit FormData en objet JSON propre
 * - Convertit les chaînes vides en null pour les champs ID
 * - Nettoie les espaces inutiles
 * - Prépare les données pour l'envoi JSON
 * 
 * @param {FormData} formData - Le FormData à convertir
 * @returns {Object} - Objet nettoyé prêt pour JSON.stringify()
 */
window.formDataToCleanObject = function(formData) {
    const data = {};
    
    for (const [key, value] of formData.entries()) {
        // Convertir les chaînes vides en null pour les champs numériques (ID)
        if (value === '' && (key.endsWith('_id') || key === 'id')) {
            data[key] = null;
        }
        // Convertir "null" string en null
        else if (value === 'null') {
            data[key] = null;
        }
        // Nettoyer les espaces pour les chaînes
        else if (typeof value === 'string') {
            data[key] = value.trim();
        }
        // Garder les autres valeurs telles quelles
        else {
            data[key] = value;
        }
    }
    
    return data;
};

/**
 * Vérifie si un FormData contient des fichiers
 * @param {FormData} formData - Le FormData à vérifier
 * @returns {boolean} - true si contient des fichiers
 */
window.formDataHasFiles = function(formData) {
    for (const [key, value] of formData.entries()) {
        if (value instanceof File && value.size > 0) {
            return true;
        }
    }
    return false;
};

/**
 * Nettoie un FormData en supprimant toutes les valeurs vides
 * Les champs vides ne seront pas envoyés (= null côté serveur pour champs optionnels)
 * 
 * IMPORTANT: Pour les fichiers, on les ajoute directement sans itérer pour éviter de les consommer
 * 
 * @param {FormData} formData - Le FormData à nettoyer
 * @returns {FormData} - Nouveau FormData nettoyé
 */
window.cleanFormData = function(formData) {
    const cleaned = new FormData();
    
    // Liste des champs obligatoires qui ne doivent JAMAIS être supprimés même s'ils sont vides
    // (pour que FastAPI puisse lever une erreur de validation)
    const requiredFields = ['sous_direction_id']; // Ajouter d'autres champs obligatoires si nécessaire
    
    // Liste des champs optionnels qui doivent être envoyés même s'ils sont vides
    // (pour permettre de les mettre à None lors d'une modification)
    const optionalFieldsToKeep = ['code', 'objectif_global_id', 'resultat_strategique_id', 'programme_id'];
    
    // Pour les fichiers, on doit les traiter différemment pour éviter de les consommer
    // On itère une seule fois et on ajoute directement les fichiers
    for (const [key, value] of formData.entries()) {
        // Si c'est un fichier, toujours l'ajouter directement (sans modification)
        if (value instanceof File) {
            // N'ajouter que si le fichier a du contenu
            if (value.size > 0) {
                cleaned.append(key, value);
            }
        }
        // Si c'est un champ obligatoire, toujours l'envoyer (même vide) pour que FastAPI puisse valider
        else if (requiredFields.includes(key)) {
            const finalValue = value === null || value === undefined ? '' : String(value);
            cleaned.append(key, finalValue);
        }
        // Si c'est un champ optionnel spécial (objectif_global_id, resultat_strategique_id),
        // toujours l'envoyer même s'il est vide (pour permettre de le mettre à None lors d'une modification)
        else if (optionalFieldsToKeep.includes(key)) {
            const finalValue = value === null || value === undefined ? '' : String(value);
            cleaned.append(key, finalValue);
        }
        // Si la valeur est vide, ne pas l'envoyer (le serveur traitera comme None pour les champs optionnels)
        // IMPORTANT: Pour les champs ID optionnels (qui se terminent par _id), on ne les envoie JAMAIS s'ils sont vides
        // car FastAPI ne peut pas convertir une chaîne vide en int | None
        else if (value === '' || value === 'null' || value === 'undefined') {
            // Ne pas ajouter les champs vides optionnels
            // FastAPI traitera l'absence du champ comme None pour les paramètres optionnels (Form(None))
        }
        // Si la valeur est remplie, l'ajouter après nettoyage des espaces
        else {
            const trimmedValue = typeof value === 'string' ? value.trim() : value;
            cleaned.append(key, trimmedValue);
        }
    }
    
    return cleaned;
};

/**
 * Helper intelligent pour envoyer des données de formulaire
 * Détecte automatiquement si le formulaire contient des fichiers :
 * - Si oui : envoie en multipart/form-data (garde FormData)
 * - Si non : envoie en JSON (convertit et nettoie)
 * 
 * @param {string} url - L'URL de destination
 * @param {FormData} formData - Le FormData du formulaire
 * @param {string} method - La méthode HTTP (POST, PUT, etc.)
 * @param {boolean} forceFormData - Forcer l'utilisation de FormData même sans fichiers
 * @returns {Promise} - La promesse du fetch
 */
window.submitFormAsJson = async function(url, formData, method = 'POST', forceFormData = false) {
    // Si le formulaire contient des fichiers ou forceFormData=true, envoyer en multipart/form-data
    // IMPORTANT: Si forceFormData=true, ne pas appeler formDataHasFiles car cela itère sur formData.entries()
    // et peut consommer le fichier avant qu'on puisse l'envoyer
    if (forceFormData || window.formDataHasFiles(formData)) {
        // Nettoyer le FormData (supprimer les valeurs vides des champs ID)
        // ATTENTION: cleanFormData itère aussi sur formData.entries(), mais c'est nécessaire
        // pour nettoyer les valeurs. Le fichier sera ajouté tel quel au nouveau FormData.
        const cleanedFormData = window.cleanFormData(formData);
        
        try {
            // Le wrapper fetch va automatiquement préfixer l'URL si elle commence par /api/
            // Pour FormData, le navigateur gère automatiquement le Content-Type avec la boundary appropriée
            const response = await window.fetch(url, {
                method: method,
                body: cleanedFormData
            });
            
            // Vérifier que response existe (ne devrait jamais arriver avec le wrapper corrigé, mais sécurité)
            if (!response) {
                throw new Error('Aucune réponse du serveur (response est undefined)');
            }
            
            return response;
        } catch (error) {
            console.error('[submitFormAsJson] Erreur fetch:', error);
            throw error;
        }
    }
    
    // Sinon, convertir en JSON et nettoyer
    const data = window.formDataToCleanObject(formData);
    
    return fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });
};

/**
 * Afficher un message de succès/erreur
 */
window.showMessage = window.showMessage || function(message, type = 'success') {
    console.log(`[${type.toUpperCase()}]`, message);
    // Cette fonction peut être surchargée par les pages individuelles
};

/**
 * Afficher un overlay de chargement
 */
window.showLoading = window.showLoading || function(text = 'Chargement...', subtext = 'Veuillez patienter') {
    console.log(`[LOADING] ${text} - ${subtext}`);
    // Cette fonction peut être surchargée par les pages individuelles
};

/**
 * Masquer l'overlay de chargement
 */
window.hideLoading = window.hideLoading || function() {
    console.log('[LOADING] Hidden');
    // Cette fonction peut être surchargée par les pages individuelles
};

// ============================================
// TRANSITIONS DE PAGE ÉLÉGANTES
// ============================================

/**
 * Ajoute des transitions fluides lors de la navigation entre les pages
 * Intercepte les clics sur les liens pour ajouter une animation de sortie
 */
(function() {
    // Attendre que le DOM soit chargé
    document.addEventListener('DOMContentLoaded', function() {
        
        // Intercepter tous les clics sur les liens internes
        document.addEventListener('click', function(e) {
            // Trouver le lien cliqué (peut être un parent du cible)
            const link = e.target.closest('a');
            
            // Vérifier si c'est un lien valide
            if (!link) return;
            
            const href = link.getAttribute('href');
            
            // Ignorer les cas suivants :
            // - Liens externes (commencent par http:// ou https://)
            // - Liens ancres (#)
            // - Liens vides ou javascript:
            // - Liens avec target="_blank"
            // - Liens avec download
            // - Clics avec Ctrl/Cmd (nouvel onglet)
            if (!href || 
                href.startsWith('http://') || 
                href.startsWith('https://') ||
                href.startsWith('#') ||
                href.startsWith('javascript:') ||
                href === '' ||
                link.target === '_blank' ||
                link.hasAttribute('download') ||
                e.ctrlKey || 
                e.metaKey) {
                return;
            }
            
            // Empêcher la navigation par défaut
            e.preventDefault();
            
            // Ajouter la classe d'animation de sortie
            document.body.classList.add('page-exit');
            
            // Naviguer après l'animation (300ms)
            setTimeout(function() {
                window.location.href = href;
            }, 300);
        });
        
        // Animation d'entrée au chargement de la page
        document.body.style.opacity = '0';
        document.body.style.transform = 'translateY(10px)';
        
        // Déclencher l'animation après un court délai
        setTimeout(function() {
            document.body.style.transition = 'opacity 0.4s ease-in-out, transform 0.4s ease-in-out';
            document.body.style.opacity = '1';
            document.body.style.transform = 'translateY(0)';
            
            // Retirer le transform après l'animation pour permettre le positionnement fixed
            setTimeout(function() {
                document.body.style.transition = 'opacity 0.4s ease-in-out';
                document.body.style.transform = '';
            }, 400); // Après la durée de l'animation (0.4s)
        }, 10);
    });
})();

// ============================================
// RESPONSIVE - GESTION DU MENU MOBILE
// ============================================

/**
 * Gestion du menu hamburger et de la sidebar sur mobile
 */
(function() {
    document.addEventListener('DOMContentLoaded', function() {
        // Toggle sidebar
        const sidebarToggle = document.querySelector('.sidebar-toggle');
        const sidebar = document.querySelector('.sidebar');
        const sidebarOverlay = document.querySelector('.sidebar-overlay');
        
        if (sidebarToggle && sidebar) {
            // Créer l'overlay s'il n'existe pas
            if (!sidebarOverlay) {
                const overlay = document.createElement('div');
                overlay.className = 'sidebar-overlay';
                document.body.appendChild(overlay);
                
                // Fermer la sidebar en cliquant sur l'overlay
                overlay.addEventListener('click', function() {
                    closeSidebar();
                });
            }
            
            // Ouvrir/fermer la sidebar
            sidebarToggle.addEventListener('click', function(e) {
                e.stopPropagation();
                toggleSidebar();
            });
            
            // Fermer la sidebar en cliquant sur un lien
            const sidebarLinks = sidebar.querySelectorAll('a');
            sidebarLinks.forEach(function(link) {
                link.addEventListener('click', function() {
                    closeSidebar();
                });
            });
            
            // Fermer la sidebar avec la touche Escape
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape' && sidebar.classList.contains('open')) {
                    closeSidebar();
                }
            });
        }
        
        function toggleSidebar() {
            if (sidebar) {
                sidebar.classList.toggle('open');
                const overlay = document.querySelector('.sidebar-overlay');
                if (overlay) {
                    overlay.classList.toggle('active');
                }
                document.body.style.overflow = sidebar.classList.contains('open') ? 'hidden' : '';
            }
        }
        
        function closeSidebar() {
            if (sidebar) {
                sidebar.classList.remove('open');
                const overlay = document.querySelector('.sidebar-overlay');
                if (overlay) {
                    overlay.classList.remove('active');
                }
                document.body.style.overflow = '';
            }
        }
        
        // Exposer les fonctions globalement
        window.toggleSidebar = toggleSidebar;
        window.closeSidebar = closeSidebar;
    });
})();
