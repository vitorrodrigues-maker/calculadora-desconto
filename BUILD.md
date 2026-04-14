# Como gerar o .exe para Windows

## Pre-requisitos

- Python 3.9+ instalado no Windows ([python.org/downloads](https://www.python.org/downloads/))
- IMPORTANTE: Marcar "Add Python to PATH" durante a instalacao

## Passo a passo

### 1. Copiar o projeto para o Windows

Copie toda a pasta do projeto para a maquina Windows.

IMPORTANTE: Coloque a pasta em um caminho SIMPLES, sem acentos e sem espacos.
Exemplos bons:
- C:\calculadora
- C:\Users\SeuNome\Desktop\calculadora

Exemplos ruins (podem causar erro):
- C:\Users\João\Meus Documentos\pasta com espaços\projeto

### 2. Rodar o build

Abra a pasta do projeto e clique 2x no arquivo `build.bat`.

Ele vai:
1. Instalar as dependencias Python
2. Instalar o PyInstaller
3. Gerar o executavel

### 3. Pegar o .exe

Apos o build, o executavel estara em:

```
dist\CalculadoraDesconto.exe
```

Tamanho estimado: 30-50 MB.

## Distribuicao

Envie o arquivo `CalculadoraDesconto.exe` para o colaborador.

Ele so precisa:
1. Baixar o arquivo
2. Clicar 2x
3. Se o Windows Defender perguntar, clicar em "Mais informacoes" > "Executar assim mesmo"
4. O navegador abre automaticamente com a calculadora
5. Manter a janela preta (console) aberta enquanto usa

## Atualizando

Se precisar atualizar (nova versao, senha mudou, etc):
1. Altere os arquivos do projeto
2. Rode `build.bat` novamente
3. Envie o novo .exe

## Solucao de problemas

### "Nao foi possivel criar arquivo de destino"
- Mova a pasta do projeto para um caminho curto sem espacos (ex: C:\calculadora)
- Clique com botao direito no build.bat > "Executar como administrador"

### "python nao e reconhecido"
- Reinstale o Python marcando "Add Python to PATH"
- Ou use o caminho completo: C:\Python39\python.exe

## Build manual (alternativa ao .bat)

```cmd
python -m pip install -r requirements.txt
python -m pip install pyinstaller
python -m PyInstaller calculadora.spec --noconfirm --clean
```
