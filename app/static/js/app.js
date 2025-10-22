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
 */
(function() {
    const originalFetch = window.fetch;
    
    window.fetch = function(url, options) {
        // Si l'URL est une chaîne et commence par /api/, /static/, ou /uploads/
        if (typeof url === 'string') {
            if (url.startsWith('/api/') || url.startsWith('/static/') || url.startsWith('/uploads/')) {
                url = window.apiUrl(url);
            }
        }
        
        // Appeler le fetch original avec l'URL préfixée
        return originalFetch(url, options);
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
 * @param {FormData} formData - Le FormData à nettoyer
 * @returns {FormData} - Nouveau FormData nettoyé
 */
window.cleanFormData = function(formData) {
    const cleaned = new FormData();
    
    for (const [key, value] of formData.entries()) {
        // Si c'est un fichier, toujours l'ajouter
        if (value instanceof File) {
            // N'ajouter que si le fichier a du contenu
            if (value.size > 0) {
                cleaned.append(key, value);
            }
        }
        // Si la valeur est vide, l'envoyer comme chaîne vide (le serveur convertira en null si besoin)
        else if (value === '' || value === 'null' || value === 'undefined') {
            cleaned.append(key, '');  // Envoyer explicitement la chaîne vide
        }
        // Si la valeur est remplie, l'ajouter après nettoyage des espaces
        else {
            cleaned.append(key, typeof value === 'string' ? value.trim() : value);
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
    if (forceFormData || window.formDataHasFiles(formData)) {
        // Nettoyer le FormData (supprimer les valeurs vides des champs ID)
        const cleanedFormData = window.cleanFormData(formData);
        return fetch(url, {
            method: method,
            body: cleanedFormData  // Pas de Content-Type, le navigateur le gère automatiquement
        });
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
        }, 10);
    });
})();
