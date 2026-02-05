"""Lightweight parser to map element IDs to part IDs from k/dyn files."""

import re
from pathlib import Path


class ElementMapper:
    """Maps element IDs to part IDs by parsing LS-DYNA input deck."""

    def __init__(self, file_path: Path | str):
        self.file_path = Path(file_path)
        self.elem_to_part: dict[int, int] = {}

    def parse(self) -> dict[int, int]:
        """Parse k/dyn file and return element→part mapping.

        Returns:
            dict: {element_id: part_id}
        """
        if not self.file_path.exists():
            return self.elem_to_part

        with open(self.file_path, 'r', encoding='utf-8', errors='replace') as f:
            in_element_block = False
            element_type = None

            for line in f:
                upper = line.upper()

                # Detect element blocks
                if upper.startswith('*ELEMENT_SOLID'):
                    in_element_block = True
                    element_type = 'solid'
                    continue
                elif upper.startswith('*ELEMENT_SHELL'):
                    in_element_block = True
                    element_type = 'shell'
                    continue
                elif upper.startswith('*ELEMENT_BEAM'):
                    in_element_block = True
                    element_type = 'beam'
                    continue
                elif upper.startswith('*'):
                    # New keyword - exit element block
                    in_element_block = False
                    element_type = None
                    continue

                if in_element_block and element_type:
                    # Skip comment lines
                    if line.startswith('$'):
                        continue

                    # Parse element line
                    # Format: EID PID N1 N2 N3 N4 ...
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            elem_id = int(parts[0])
                            part_id = int(parts[1])
                            self.elem_to_part[elem_id] = part_id
                        except (ValueError, IndexError):
                            pass

        return self.elem_to_part


def find_and_parse_input_deck(result_dir: Path) -> dict[int, int]:
    """Find k or dyn file in result directory and parse element mapping.

    Search order:
    1. *.k files in directory
    2. dynain file (restart input)
    3. *.dyn files

    Args:
        result_dir: Path to simulation result directory

    Returns:
        dict: {element_id: part_id} mapping, empty if no file found
    """
    # Try .k files first
    k_files = list(result_dir.glob('*.k'))
    if k_files:
        # Prefer main deck files (not include files)
        for kfile in k_files:
            if not kfile.name.startswith('include'):
                mapper = ElementMapper(kfile)
                return mapper.parse()
        # If all are includes, just use first
        mapper = ElementMapper(k_files[0])
        return mapper.parse()

    # Try dynain (restart input)
    dynain = result_dir / 'dynain'
    if dynain.exists():
        mapper = ElementMapper(dynain)
        return mapper.parse()

    # Try .dyn files
    dyn_files = list(result_dir.glob('*.dyn'))
    if dyn_files:
        mapper = ElementMapper(dyn_files[0])
        return mapper.parse()

    return {}
