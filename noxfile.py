import nox


@nox.session
def tests(session: nox.Session) -> None:
    session.install("-r", "requirements.txt")
    try:
        session.install("-r", "requirements-dev.txt")
    except Exception:
        pass
    session.run("pytest", "-q")


@nox.session
def lint(session: nox.Session) -> None:
    session.install("ruff")
    session.run("ruff", "check", ".")
    # fallback flake8 if needed
    try:
        session.install("flake8")
        session.run("flake8", ".")
    except Exception:
        pass


@nox.session
def typecheck(session: nox.Session) -> None:
    session.install("mypy")
    session.run("mypy", "--install-types", "--non-interactive", ".")


@nox.session
def format(session: nox.Session) -> None:
    session.install("black")
    session.run("black", ".")
