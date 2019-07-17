import click
import toml

from bridge.config import load_config


@click.command()
@click.option(
    "-c", "--config", "config_path", type=click.Path(exists=True), default=None
)
def main(config_path):
    try:
        config = load_config(config_path)
    except toml.decoder.TomlDecodeError as decode_error:
        raise click.UsageError(
            f"Error in config file: {decode_error}"
        ) from decode_error
    except ValueError as value_error:
        raise click.UsageError(f"Error in config file: {value_error}") from value_error

    print(config)
