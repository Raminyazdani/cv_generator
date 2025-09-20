from pathlib import Path
from dispatcher import HANDLERS
from io_utils import read_json, write_text

DATA_IN = Path("../data/my_cv.json").resolve()
DATA_OUT = Path("../data/data.tex").resolve()

def main():
    # TODO: validate DATA_IN exists; handle errors gracefully
    cv = read_json(DATA_IN)

    # TODO: configurable section order; for now use HANDLERS order
    outputs = []
    for key, handler in HANDLERS.items():
        section_data = cv.get(key, None)
        if section_data is None:
            # TODO: warn if key missing
            continue
        # TODO: each handler returns LaTeX string
        outputs.append(handler(section_data))

    # TODO: join outputs with newlines and write to DATA_OUT
    write_text(DATA_OUT, "\n".join(outputs))

if __name__ == "__main__":
    main()
