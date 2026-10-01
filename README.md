# Área Local

Projeto de estudos em Flask para rodar apenas no computador. Inclui cadastro, login, perfil e administração de usuários. Os números do painel são ilustrativos.

## Iniciar no Windows (PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Abra `http://127.0.0.1:5000/`. A aplicação escuta somente em `127.0.0.1` quando iniciada por `python app.py`.

## Administrador

Não existe mais uma conta administrativa criada com senha padrão. Para criar uma ou atualizar a senha de uma conta existente:

```powershell
flask --app app create-admin
```

O comando pede nome, email e senha (mínimo de 12 caracteres). Na primeira execução, a aplicação desativa o acesso administrativo de qualquer conta herdada que ainda use a antiga senha de exemplo `222`. Essa conta pode ser reativada pelo comando acima, usando o mesmo email e uma nova senha.

## Estrutura

```text
app.py                      ponto de entrada local
training_app/
  __init__.py               configuração e fábrica da aplicação
  auth.py                   cadastro, login e conta
  admin.py                  administração
  main.py                   painel e perfil
  models.py                 modelo SQLAlchemy
  validation.py             validação dos dados
  security.py               CSRF e cabeçalhos de segurança
  templates/                páginas Jinja e layout base
  static/css/app.css        estilos responsivos
instance/                   banco SQLite e chave local de sessão
```

O arquivo `instance/db.sqlite` existente é reutilizado. Antes da primeira inicialização da nova versão, foi criada uma cópia em `instance/db.sqlite.backup-before-refactor`. O banco guarda os usuários e não deve ser publicado. `instance/secret_key` é gerado automaticamente e também deve permanecer privado. Esses arquivos estão no `.gitignore`.

Todos os formulários POST incluem um token CSRF. O logout e as exclusões usam POST. A senha é armazenada com bcrypt, e a sessão usa cookie `HttpOnly` com `SameSite=Lax`. Como o uso é local via HTTP, o cookie não usa `Secure`; se a aplicação for publicada ou exposta em rede, será necessário configurar HTTPS e rever a implantação.

## Testes

```powershell
python -m unittest discover -s tests -v
```
