// CAPTURA DOS ELEMENTOS

const conversa = document.getElementById("conversa");
const listaMensagens = document.getElementById("listaMensagens");
const mensagemInicial = document.getElementById("mensagemInicial");
const digitando = document.getElementById("digitando");
const inputPergunta = document.getElementById("inputPergunta");
const botaoEnviar = document.getElementById("botaoEnviar");

// variaveis

let historico = [];

// resgata ou cria o id da sessao

let sessaoId = localStorage.getItem("sessao_id");

if (!sessaoId) {
    sessaoId = crypto.randomUUID();
    localStorage.setItem("sessao_id", sessaoId);
}


// ESCONDE O "DIGITANDO"

digitando.style.display = "none";

// EVENTOS

botaoEnviar.addEventListener("click", enviarPergunta);

inputPergunta.addEventListener("keydown", function (event) {

    if (event.key === "Enter") {

        enviarPergunta();

    }

});

// BOTÕES DE SUGESTÃO

const categorias = document.querySelectorAll(".sugestao-btn");

categorias.forEach(botao => {

    botao.addEventListener("click", () => {

        botao.classList.toggle("ativo");

        const submenu = botao.nextElementSibling;

        submenu.classList.toggle("ativo");

    });

});
const perguntas = document.querySelectorAll(".pergunta");

perguntas.forEach(pergunta => {

    pergunta.addEventListener("click", () => {

        inputPergunta.value = pergunta.textContent.trim();

        inputPergunta.focus();

        botaoEnviar.click();

    });

});


// ENVIAR PERGUNTA

async function enviarPergunta() {

    const pergunta = inputPergunta.value.trim();

    if (pergunta === "") return;

    if (mensagemInicial) {
        mensagemInicial.style.display = "none";
    }

    // Mostra a pergunta na tela
    adicionarMensagem(pergunta, "usuario");

    // Adiciona ao histórico
    historico.push({
        autor: "usuario",
        texto: pergunta
    });

    inputPergunta.value = "";

    digitando.style.display = "flex";

    rolarConversa();

    try {

        const resposta = await fetch(
            "http://127.0.0.1:8000/chat",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    pergunta: pergunta,
                    historico: historico,
                    sessao_id: sessaoId
                })
            }
        );

        if (!resposta.ok) {
            throw new Error(
                `Erro HTTP: ${resposta.status}`
            );
        }

        const dados = await resposta.json();

        digitando.style.display = "none";

        // Mostra resposta da IA
        adicionarMensagem(
            dados.resposta,
            "bot"
        );

        // Adiciona resposta ao histórico
        historico.push({
            autor: "bot",
            texto: dados.resposta
        });

        // Mantém somente as últimas 20 mensagens
        if (historico.length > 20) {
            historico = historico.slice(-20);
        }

        rolarConversa();

    } catch (erro) {

        digitando.style.display = "none";

        adicionarMensagem(
            "Erro ao conectar com o servidor.",
            "sistema"
        );

        console.error(erro);
    }
}
// ADICIONA MENSAGENS

function adicionarMensagem(texto, tipo) {

    const mensagem = document.createElement("div");

    mensagem.classList.add("mensagem");

    mensagem.classList.add(tipo);

    mensagem.innerText = texto;

    listaMensagens.appendChild(mensagem);

}

// ROLAR CONVERSA

function rolarConversa() {

    conversa.scrollTop = conversa.scrollHeight;

}
