// CAPTURA DOS ELEMENTOS

const conversa = document.getElementById("conversa");
const listaMensagens = document.getElementById("listaMensagens");
const mensagemInicial = document.getElementById("mensagemInicial");
const digitando = document.getElementById("digitando");

const inputPergunta = document.getElementById("inputPergunta");
const botaoEnviar = document.getElementById("botaoEnviar");

// ESCONDE O "DIGITANDO"

digitando.style.display = "none";

// EVENTOS

botaoEnviar.addEventListener("click", enviarPergunta);

inputPergunta.addEventListener("keydown", function (event) {

    if (event.key === "Enter") {

        enviarPergunta();

    }

});

// ENVIAR PERGUNTA

let historico = [];

async function enviarPergunta() {

    const pergunta = inputPergunta.value.trim();

    if (pergunta === "") return;

    if (mensagemInicial) {

        mensagemInicial.style.display = "none";

    }

    adicionarMensagem(pergunta, "usuario");

    // Salva no histórico
    historico.push({
        autor: "usuario",
        texto: pergunta
    });

    inputPergunta.value = "";

    digitando.style.display = "block";

    rolarConversa();


    // envio para o backend
    try {
        const resposta = await fetch(
            "http://127.0.0.1:8000/chat",
            {
                method: "POST",
                headers: {
                    "Content-type": "application/json"
                },
                body: JSON.stringify({
                    pergunta: pergunta,
                    historico: historico
                })
            }
        );


        const dados = await resposta.json();

        adicionarMensagem(dados.resposta, "IA");

         historico.push({
            autor: "IA",
            texto: dados.resposta
        });

         if(historico.length > 20){
            historico = historico.slice(-20);
        }

        rolarConversa();
    }catch(erro){

        digitando.style.display = "none";

        adicionarMensagem(
            "Erro ao conectar com o servidor.",
            "sitema"
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