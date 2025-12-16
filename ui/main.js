// main.js - Production Ready Version
const API_BASE = "http://localhost:8000";

/**
 * INDEX PAGE LOGIC
 */

async function loadPrices() {
    const btcEl = document.getElementById("btcPrice");
    const ethEl = document.getElementById("ethPrice");
    const dogeEl = document.getElementById("dogePrice");

    // Safety guard: stop if we aren't on the page with these IDs
    if (!btcEl && !ethEl && !dogeEl) return; 

    try {
        const res = await fetch(`${API_BASE}/crypto_data`);
        if (!res.ok) throw new Error("Server response was not ok");
        
        const data = await res.json();

        data.forEach(coin => {
            // Matching based on typical CoinGecko ID naming
            if (coin.id === 'bitcoin' && btcEl) btcEl.innerText = `$${coin.current_price.toLocaleString()}`;
            if (coin.id === 'ethereum' && ethEl) ethEl.innerText = `$${coin.current_price.toLocaleString()}`;
            if (coin.id === 'dogecoin' && dogeEl) dogeEl.innerText = `$${coin.current_price.toLocaleString()}`;
        });
    } catch (err) {
        console.error("Price fetch failed:", err);
    }
}


/**
 * LIVE DASHBOARD TABLE
 */
function formatNumber(num) {
    if (num >= 1e9) return (num / 1e9).toFixed(2) + "B";
    if (num >= 1e6) return (num / 1e6).toFixed(2) + "M";
    return num.toLocaleString();
}

async function updateDashboard() {
    try {
        // 1. Fetch Global Metadata (Market Cap, Dominance, Active Cryptos)
        const globalResponse = await fetch('https://api.coingecko.com/api/v3/global');
        const globalData = await globalResponse.json();
        const stats = globalData.data;

        // Map data to HTML IDs
        document.getElementById("totalMarketCap").innerText = `$${(stats.total_market_cap.usd / 1e12).toFixed(2)}T`;
        document.getElementById("totalVolume24h").innerText = `$${(stats.total_volume.usd / 1e9).toFixed(2)}B`;
        document.getElementById("btcDominance").innerText = `${stats.market_cap_percentage.btc.toFixed(1)}%`;
        document.getElementById("activeCount").innerText = stats.active_cryptocurrencies.toLocaleString();

        // 2. Fetch Detailed Market Facts (Top 50 Coins)
        const coinResponse = await fetch('https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=50&page=1&sparkline=false');
        const coins = await coinResponse.json();

        renderTable(coins);
        renderCharts(coins.slice(0, 10)); // Display top 10 in visual charts

    } catch (error) {
        console.error("Data retrieval failed:", error);
        document.querySelectorAll(".metric-card p").forEach(p => p.innerText = "Error");
    }
}

function renderTable(data) {
    const tableBody = document.getElementById("cryptoTableBody");
    tableBody.innerHTML = data.map(coin => `
        <tr>
            <td>${coin.market_cap_rank}</td>
            <td><strong>${coin.name}</strong></td>
            <td>${coin.symbol.toUpperCase()}</td>
            <td>$${coin.current_price.toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
            <td style="color: ${coin.price_change_percentage_24h >= 0 ? '#27ae60' : '#e74c3c'}; font-weight: bold;">
                ${coin.price_change_percentage_24h?.toFixed(2)}%
            </td>
            <td>$${(coin.market_cap / 1e9).toFixed(2)}B</td>
            <td>$${(coin.total_volume / 1e9).toFixed(2)}B</td>
        </tr>
    `).join('');
}

function renderCharts(topTen) {
    const labels = topTen.map(c => c.symbol.toUpperCase());
    const prices = topTen.map(c => c.current_price);
    const changes = topTen.map(c => c.price_change_percentage_24h);

    // Price Chart Configuration
    const priceData = [{
        x: labels,
        y: prices,
        type: 'bar',
        marker: { color: '#4a90e2' }
    }];

    // Performance Chart Configuration
    const changeData = [{
        x: labels,
        y: changes,
        type: 'bar',
        marker: { color: changes.map(v => v >= 0 ? '#27ae60' : '#e74c3c') }
    }];

    const layout = { height: 350, margin: { t: 20, b: 40, l: 40, r: 20 } };

    Plotly.newPlot('chart-prices', priceData, layout);
    Plotly.newPlot('chart-changes', changeData, layout);
}

// Initial Load
updateDashboard();

// Auto-refresh every 60 seconds (aligned with API rate limits)
setInterval(updateDashboard, 60000);


// evaluation
const API_URL = "http://127.0.0.1:8000";
function setSampleQuery(text) {
    document.getElementById("evalQuery").value = text;
    runEvaluation();
}

async function runEvaluation() {
    const query = document.getElementById("evalQuery").value;
    if (!query) return;

    // Reset UI and show loading
    document.getElementById("ragAnswer").innerText = "Generating RAG Response...";
    document.getElementById("nonRagAnswer").innerText = "Generating Standard Response...";

    // 1. Fetch RAG response
    const ragRes = await fetch("http://localhost:8000/generate_answer", {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query, use_rag: true })
    });
    const ragData = await ragRes.json();

    // 2. Fetch Non-RAG response
    const stdRes = await fetch("http://localhost:8000/generate_answer", {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query, use_rag: false })
    });
    const stdData = await stdRes.json();

    // Update Metrics Cards
    document.getElementById("factsRAG").innerText = ragData.facts_used;
    document.getElementById("genTimeRAG").innerText = ragData.generation_time.toFixed(2) + "s";
    
    // Display Answers
    document.getElementById("ragAnswer").innerText = ragData.answer;
    document.getElementById("nonRagAnswer").innerText = stdData.answer;

    // --- CHART SECTION START ---
    const chartData = [
        {
            x: ['RAG-Enhanced', 'Standard LLM'],
            y: [ragData.generation_time, stdData.generation_time],
            type: 'bar',
            marker: {
                color: ['#00ffcc', '#ff3366'] // Neon green for RAG, pink/red for Standard
            }
        }
    ];

    const layout = {
        title: 'Response Generation Time (Seconds)',
        paper_bgcolor: 'rgba(0,0,0,0)', // Transparent background to match your CSS
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#fff' }, // White text for dark mode
        yaxis: {
            title: 'Seconds',
            gridcolor: '#444'
        },
        margin: { t: 50, b: 50, l: 50, r: 20 }
    };

    Plotly.newPlot('perfChart', chartData, layout);
    // --- CHART SECTION END ---
}
/**
 * AI CHAT LOGIC
 */
async function askAI() {
    const inputField = document.getElementById('chat-input-field');
    const query = inputField.value.trim();
    if (!query) return;

    appendMessage('user', query); // Helper to add user bubble
    inputField.value = '';

    try {
        const response = await fetch("http://localhost:8000/generate_answer", {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query, use_rag: true })
        });
        const data = await response.json();
        
        // Display answer with "Live Facts" and "Time" badges matching your UI
        const aiHtml = `
            <p>${data.answer}</p>
            <div class="ai-metadata">
                <span class="fact-badge">📖 ${data.facts_used} Live Facts</span>
                <span class="time-badge">⏱️ ${data.generation_time.toFixed(2)}s</span>
            </div>`;
        appendMessage('ai', aiHtml);
    } catch (err) {
        appendMessage('ai', "Error connecting to AI service.");
    }
}
// knowledge
/**
 * KNOWLEDGE EXPLORER LOGIC
 */

/**
 * Initialize Knowledge Explorer
 */
document.addEventListener('DOMContentLoaded', () => {
    // Load stats on page load
    loadKnowledgeStats();

    // Bind search button
    const searchBtn = document.querySelector('.search-btn');
    if (searchBtn) searchBtn.addEventListener('click', searchKnowledgeBase);

    // Bind Enter key to search input
    const searchInput = document.querySelector('.search-input');
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') searchKnowledgeBase();
        });
    }

    // Bind Update Knowledge button
    const updateBtn = document.getElementById('update-db-btn');
    if (updateBtn) updateBtn.addEventListener('click', triggerKnowledgeUpdate);
});

/**
 * Load system statistics (facts & unique cryptos)
 */
async function loadKnowledgeStats() {
    try {
        const res = await fetch(`${API_BASE}/system_stats`);
        const data = await res.json();

        // Sidebar
        const factsEl = document.getElementById("total-facts-val");
        const coinsEl = document.getElementById("unique-coins-val");
        if (factsEl) factsEl.innerText = data.total_facts || 0;
        if (coinsEl) coinsEl.innerText = data.unique_coins || 0;

        // Main content stats
        document.querySelectorAll('.metric-value').forEach((el) => {
            const parentText = el.parentElement.innerText.toLowerCase();
            if (parentText.includes("total facts")) el.textContent = data.total_facts || 0;
            if (parentText.includes("unique") || parentText.includes("cryptocurrencies")) el.textContent = data.unique_coins || 0;
        });

    } catch (err) {
        console.error("Failed to fetch system stats:", err);
    }
}

/**
 * Trigger Knowledge Base Update
 */
async function triggerKnowledgeUpdate() {
    const btn = document.getElementById('update-db-btn');
    const statusText = document.getElementById('update-status');

    btn.disabled = true;
    btn.innerHTML = "🔄 Updating...";
    statusText.style.color = "#aaa";
    statusText.innerText = "Connecting to backend and re-indexing...";

    try {
        const res = await fetch(`${API_BASE}/update_knowledge`, { method: 'POST' });
        const data = await res.json();

        if (data.status === "success") {
            statusText.style.color = "#00ffcc";
            statusText.innerText = `✅ Success! ${data.message}`;
            // Refresh stats after short delay
            setTimeout(loadKnowledgeStats, 1000);
        } else {
            throw new Error(data.message || "Unknown error");
        }
    } catch (err) {
        statusText.style.color = "#ff3366";
        statusText.innerText = `❌ Update failed: ${err.message}`;
    } finally {
        btn.disabled = false;
        btn.innerText = "🔄 Update Knowledge Base";
    }
}

/**
 * Search Knowledge Base using RAG
 */
async function searchKnowledgeBase() {
    const queryInput = document.querySelector('.search-input');
    const container = document.querySelector('.fact-cards');

    if (!queryInput || !container) return;

    const query = queryInput.value.trim();
    if (!query) return;

    container.innerHTML = `<p class="loading-state">🔍 Querying Vector Database...</p>`;

    try {
        const res = await fetch(`${API_BASE}/generate_answer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query, use_rag: true })
        });

        const data = await res.json();
        container.innerHTML = "";

        if (data.retrieved_facts && data.retrieved_facts.length > 0) {
            data.retrieved_facts.forEach((fact, index) => {
                const card = document.createElement('div');
                card.className = 'fact-card';
                card.innerHTML = `
                    <div class="fact-badge">SIMILARITY: ${(fact.score ? fact.score.toFixed(3) : 'N/A')}</div>
                    <h3>📄 Verified Fact ${index + 1}</h3>
                    <p>${fact.content}</p>
                    <pre class="metadata">${JSON.stringify(fact.metadata, null, 2)}</pre>
                `;
                container.appendChild(card);
            });
        } else {
            container.innerHTML = `<p class="info-msg">No direct matches found. Try a different query.</p>`;
        }

    } catch (err) {
        container.innerHTML = `<p class="error-msg">❌ Connection lost. Is the backend running?</p>`;
        console.error("Knowledge search error:", err);
    }
}
// // UPDATE startApp to include the new loader
// function startApp() {
//     console.log("App Starting...");
//     loadIndexData();
//     loadLiveDashboard();
//     loadKnowledgeStats(); // ADD THIS LINE

//     // Add search button listener
//     const searchBtn = document.querySelector('.search-btn');
//     if (searchBtn) {
//         searchBtn.onclick = searchKnowledgeBase;
//     }
//     // ... rest of your startApp logic
// }
// Update your startApp() to include these new functions
function startApp() {
    loadIndexData();
    loadLiveDashboard();
    loadKnowledgeStats(); // New initialization 
    
    // Add listener for search button
    const searchBtn = document.querySelector('.search-btn');
    if (searchBtn) searchBtn.onclick = searchKnowledgeBase;
}
/**
 * UI HELPERS
 */
function appendMessage(sender, text, id = null) {
    const chatBody = document.getElementById('chat-body');
    if (!chatBody) return;
    
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}`;
    if (id) msgDiv.id = id;
    msgDiv.innerHTML = `<p>${text}</p>`;
    chatBody.appendChild(msgDiv);
    chatBody.scrollTop = chatBody.scrollHeight;
}

/**
 * INITIALIZATION
 */
function appendMessage(sender, text, id = null) {
    const chatBody = document.getElementById('chat-body');
    if (!chatBody) return;
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}`;
    if (id) msgDiv.id = id;
    msgDiv.innerHTML = `<p>${text}</p>`;
    chatBody.appendChild(msgDiv);
}

function startApp() {
    console.log("App Initializing...");
    loadPrices();
    updateDashboard();

    const inputField = document.querySelector('.chat-input input');
    if (inputField) {
        inputField.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') askAI();
        });
    }
}

// Global start
window.addEventListener("DOMContentLoaded", startApp);