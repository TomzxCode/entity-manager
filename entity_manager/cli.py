from cyclopts import App

app = App()


@app.default
def hello() -> None:
    """Print Hello World."""
    print("Hello World")


if __name__ == "__main__":
    app()
