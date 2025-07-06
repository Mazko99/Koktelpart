const socket = io();

function sendMessage() {
    const msg = document.getElementById("msg_input").value;
    socket.emit('send_message', { user: username, msg });
    document.getElementById("msg_input").value = "";
}

function sendPrivate() {
    const to = document.getElementById("to_user").value;
    const msg = document.getElementById("private_msg").value;
    socket.emit('private_message', { from: username, to, msg });
}

socket.on('receive_message', function(data) {
    const box = document.getElementById("chatbox");
    box.innerHTML += `<p><b>${data.user}:</b> ${data.msg}</p>`;
    box.scrollTop = box.scrollHeight;
});

socket.on('receive_private', function(data) {
    alert(`Приватное сообщение от ${data.from}:
` + data.msg);
});

socket.on('update_user_list', function(users) {
    const list = document.getElementById("user_list");
    list.innerHTML = '';
    users.forEach(u => {
        const li = document.createElement("li");
        li.className = "list-group-item";
        li.innerText = u;
        list.appendChild(li);
    });
});