const contentDiv = document.getElementById('content');
const WS_URL = 'ws://localhost:8000/ws';
let ws;

function connect() {
    ws = new WebSocket(WS_URL);
    
    ws.onopen = () => {
        console.log("Connected to local brain");
    };
    
    ws.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            if (msg.type === "config") {
                const conf = msg.data;
                document.documentElement.style.setProperty('--bg-opacity', conf.overlay_opacity);
                document.documentElement.style.setProperty('--overlay-width', conf.overlay_width_vw + 'vw');
            } else if (msg.type === "status") {
                contentDiv.innerHTML = `<em>${msg.data}</em><br><br>`;
            } else if (msg.type === "token") {
                contentDiv.innerHTML += msg.data;
                const container = document.getElementById('container');
                container.scrollTop = container.scrollHeight;
            } else if (msg.type === "done") {
                contentDiv.innerHTML += "<br><br><em>[Done]</em>";
            } else if (msg.type === "error") {
                contentDiv.innerHTML = `<span style="color: red;">Error: ${msg.data}</span>`;
            }
        } catch (e) {
            console.error(e);
        }
    };
    
    ws.onclose = () => {
        setTimeout(connect, 2000);
    };
}

connect();
