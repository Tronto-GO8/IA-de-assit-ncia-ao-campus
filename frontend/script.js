// CAPTURA DOS ELEMENTOS

const conversa = document.getElementById("conversa");
const listaMensagens = document.getElementById("listaMensagens");
const mensagemInicial = document.getElementById("mensagemInicial");
const digitando = document.getElementById("digitando");
const inputPergunta = document.getElementById("inputPergunta");
const botaoEnviar = document.getElementById("botaoEnviar");
const sessaoId = crypto.randomUUID();




//

let permitirSalvar = localStorage.getItem("permitir_salvar") === "true";

let historico = [];

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

const categorias =
document.querySelectorAll(".sugestao-btn");

categorias.forEach(botao=>{

    botao.addEventListener("click",()=>{

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

        adicionarMensagem(dados.resposta, "bot");

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



// botao de salvamento (temporário)

const botaoPermissao = document.getElementById("toggleSalvar");

atualizarBotao();

botaoPermissao.addEventListener("click", () => {

    permitirSalvar = !permitirSalvar;

    localStorage.setItem(
        "permitir_salvar",
        permitirSalvar
    );

    atualizarBotao();
});

function atualizarBotao() {

    botaoPermissao.textContent = permitirSalvar
        ? "Salvar conversas: ATIVADO"
        : "Salvar conversas: DESATIVADO";
}



// enviar conversa para o backend quando a página for fechada para os dados serem salva no banco de dados

window.addEventListener("beforeunload", () => {

    if (!permitirSalvar) return;

    if (historico.length === 0) return;

    const sessaoId =
        localStorage.getItem("sessao_id")
        || crypto.randomUUID();

    localStorage.setItem("sessao_id", sessaoId);

    const payload = {
        sessao_id: sessaoId,
        mensagens: historico,
        consentimento: true,
        modelo: "gemini-3.5-flash"
    };

    navigator.sendBeacon(
        "http://127.0.0.1:8000/feedback",
        new Blob(
            [JSON.stringify(payload)],
            { type: "application/json" }
        )
    );
});
