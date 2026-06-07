# 📱 SOCIAL SHARING
# Share buttons para WhatsApp, Facebook, Twitter, LinkedIn

from fastapi import FastAPI
import urllib.parse

def setup_social_sharing(app: FastAPI):
    """Setup social sharing endpoints"""

    @app.post("/api/share/{content_type}/{content_id}")
    def generate_share_link(
        content_type: str,  # "news" ou "event"
        content_id: int,
        platform: str = "whatsapp",  # whatsapp, facebook, twitter, linkedin
        db: Session = Depends(get_db)
    ):
        """Gerar link de compartilhamento para rede social"""

        # Buscar conteúdo
        if content_type == "news":
            content = db.query(LocalNews).filter(LocalNews.id == content_id).first()
            base_url = f"/news/{content_id}"
            title = content.title
            description = content.content[:100]
        elif content_type == "event":
            content = db.query(LocalEvent).filter(LocalEvent.id == content_id).first()
            base_url = f"/events/{content_id}"
            title = content.title
            description = f"{content.date} - {content.location}"
        else:
            raise HTTPException(status_code=400, detail="Invalid content type")

        if not content:
            raise HTTPException(status_code=404, detail="Content not found")

        # Gerar mensagem
        app_url = "https://timemates.onrender.com"
        full_url = f"{app_url}{base_url}"

        message = f"{title}\n\n{description}\n\n{full_url}"

        # Gerar links por plataforma
        share_links = {
            "whatsapp": f"https://wa.me/?text={urllib.parse.quote(message)}",
            "facebook": f"https://www.facebook.com/sharer/sharer.php?u={full_url}",
            "twitter": f"https://twitter.com/intent/tweet?text={urllib.parse.quote(f'{title} - TimeMates')}&url={full_url}",
            "linkedin": f"https://www.linkedin.com/sharing/share-offsite/?url={full_url}",
            "copy": full_url
        }

        return {
            "success": True,
            "platform": platform,
            "url": share_links.get(platform, share_links["copy"]),
            "message": message,
            "all_links": share_links
        }


# FRONTEND - SHARE BUTTONS
"""
<!-- Em public/news-dashboard.html e events-dashboard.html -->

<div class="share-buttons">
    <button onclick="shareOnWhatsApp(newsId)" class="btn-share whatsapp">
        💬 WhatsApp
    </button>
    <button onclick="shareOnFacebook(newsId)" class="btn-share facebook">
        📘 Facebook
    </button>
    <button onclick="shareOnTwitter(newsId)" class="btn-share twitter">
        𝕏 Twitter
    </button>
    <button onclick="shareOnLinkedIn(newsId)" class="btn-share linkedin">
        💼 LinkedIn
    </button>
    <button onclick="copyLink(newsId)" class="btn-share copy">
        🔗 Copy Link
    </button>
</div>

<script>
// Gerar share links
async function generateShareLink(contentType, contentId, platform) {
    const response = await fetch(`/api/share/${contentType}/${contentId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ platform })
    });

    const data = await response.json();
    return data.url;
}

// Share para WhatsApp
async function shareOnWhatsApp(contentId) {
    const url = await generateShareLink('news', contentId, 'whatsapp');
    window.open(url, '_blank');
}

// Share para Facebook
async function shareOnFacebook(contentId) {
    const url = await generateShareLink('news', contentId, 'facebook');
    window.open(url, '_blank');
}

// Share para Twitter
async function shareOnTwitter(contentId) {
    const url = await generateShareLink('news', contentId, 'twitter');
    window.open(url, '_blank');
}

// Share para LinkedIn
async function shareOnLinkedIn(contentId) {
    const url = await generateShareLink('news', contentId, 'linkedin');
    window.open(url, '_blank');
}

// Copiar link
async function copyLink(contentId) {
    const response = await fetch(`/api/share/news/${contentId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ platform: 'copy' })
    });

    const data = await response.json();

    navigator.clipboard.writeText(data.url);
    alert('Link copied! ✅');
}

// Rastrear shares (analytics)
async function trackShare(contentId, platform) {
    await fetch('/api/analytics/share', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            content_id: contentId,
            platform: platform,
            timestamp: new Date().toISOString()
        })
    });
}
</script>

<style>
.share-buttons {
    display: flex;
    gap: 10px;
    margin: 20px 0;
    flex-wrap: wrap;
}

.btn-share {
    padding: 10px 15px;
    border: none;
    border-radius: 5px;
    cursor: pointer;
    font-weight: bold;
    transition: all 0.3s;
}

.btn-share.whatsapp {
    background: #25D366;
    color: white;
}

.btn-share.facebook {
    background: #1877F2;
    color: white;
}

.btn-share.twitter {
    background: #000000;
    color: white;
}

.btn-share.linkedin {
    background: #0A66C2;
    color: white;
}

.btn-share.copy {
    background: #666;
    color: white;
}

.btn-share:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
}
</style>
"""

# DATABASE TABLE PARA ANALYTICS
"""
CREATE TABLE share_analytics (
    id SERIAL PRIMARY KEY,
    content_type VARCHAR(50),
    content_id INTEGER,
    platform VARCHAR(50),
    user_id INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Endpoint para analytics
@app.get("/api/analytics/top-shared")
def get_top_shared(db: Session = Depends(get_db)):
    # Top 10 notícias/eventos mais compartilhados
    shared = db.execute('''
        SELECT content_id, platform, COUNT(*) as count
        FROM share_analytics
        GROUP BY content_id, platform
        ORDER BY count DESC
        LIMIT 10
    ''')
    return shared
"""
