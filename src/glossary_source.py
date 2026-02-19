"""Glossary source document for NotebookLM notebooks.

This module provides the chess terminology glossary that gets added
as a source document to user notebooks, ensuring AI uses correct
chess terminology when responding in Spanish.

The glossary contains all 58 verified chess terms from Phase 3.
"""

from typing import Any

import structlog

logger = structlog.get_logger()


# Complete chess terminology glossary matching Phase 3 seed_glossary.py
# Contains all 58 verified terms organized by category
GLOSSARY_SOURCE_TEMPLATE = """# Chess Terminology Glossary (English-Spanish)

This notebook uses the following verified chess terminology translations.
When responding in Spanish, ALWAYS use these exact terms.

## IMPORTANT RULES

1. Chess notation (Nf3, Bxe5, O-O, exd5, e8=Q) is UNIVERSAL - NEVER translate it
2. ECO codes (C50, B90, E00) are UNIVERSAL - NEVER translate them
3. Use the exact Spanish terms from this glossary
4. Descriptive explanations should be in the user's preferred language
5. When explaining moves: "el caballo se mueve a f3" but notation stays "Nf3"

---

## Chess Pieces

| English | Spanish | Notes |
|---------|---------|-------|
| king | rey | The most important piece |
| queen | dama | NOT "reina" - use "dama" for chess |
| rook | torre | Moves horizontally and vertically |
| bishop | alfil | NOT "obispo" - that's the religious bishop |
| knight | caballo | NOT "caballero" - that's a gentleman |
| pawn | peon | Can promote on reaching opposite rank |

---

## Tactics

| English | Spanish | Notes |
|---------|---------|-------|
| fork | horquilla | NOT "tenedor" - that's a fork for eating |
| pin | clavada | Piece cannot move without exposing more valuable piece |
| skewer | pincho | Like a pin but attacking more valuable piece first |
| discovered attack | ataque descubierto | Moving one piece reveals attack by another |
| double check | jaque doble | Check from two pieces simultaneously |
| sacrifice | sacrificio | Giving up material for advantage |
| checkmate | jaque mate | King under attack with no escape |
| stalemate | ahogado | No legal moves but not in check - draw |
| check | jaque | NOT "cheque" - that's a bank check |
| perpetual check | jaque perpetuo | Endless series of checks leading to draw |
| zugzwang | zugzwang | German term used in Spanish; any move worsens position |
| deflection | desviacion | Forcing a defending piece away |
| decoy | atraccion | Luring a piece to a bad square |
| overloading | sobrecarga | Piece with too many defensive duties |
| trapped piece | pieza atrapada | Piece with no safe squares |
| back rank mate | mate de pasillo | Checkmate on the back rank |
| smothered mate | mate ahogado | Knight mate where king trapped by own pieces |

---

## Openings

| English | Spanish | Moves |
|---------|---------|-------|
| Italian Game | Apertura Italiana | 1.e4 e5 2.Nf3 Nc6 3.Bc4 |
| Sicilian Defense | Defensa Siciliana | 1.e4 c5 |
| French Defense | Defensa Francesa | 1.e4 e6 |
| Caro-Kann Defense | Defensa Caro-Kann | 1.e4 c6 |
| Ruy Lopez | Apertura Espanola | 1.e4 e5 2.Nf3 Nc6 3.Bb5 |
| Spanish Game | Apertura Espanola | Same as Ruy Lopez |
| Queen's Gambit | Gambito de Dama | 1.d4 d5 2.c4 |
| King's Indian Defense | Defensa India de Rey | Hypermodern vs 1.d4 |
| English Opening | Apertura Inglesa | 1.c4 |
| Dragon Variation | Variante del Dragon | Sicilian with g6 and Bg7 |
| Najdorf Variation | Variante Najdorf | Sicilian 5...a6 |
| Scotch Game | Apertura Escocesa | 1.e4 e5 2.Nf3 Nc6 3.d4 |
| Pirc Defense | Defensa Pirc | 1.e4 d6 |
| Grunfeld Defense | Defensa Grunfeld | 1.d4 Nf6 2.c4 g6 3.Nc3 d5 |
| Nimzo-Indian Defense | Defensa Nimzoindia | 1.d4 Nf6 2.c4 e6 3.Nc3 Bb4 |
| King's Gambit | Gambito de Rey | 1.e4 e5 2.f4 |
| London System | Sistema Londres | Solid d4, Bf4 setup |

---

## Strategy

| English | Spanish | Notes |
|---------|---------|-------|
| castling | enroque | Special king+rook move |
| kingside castling | enroque corto | O-O - towards h-file |
| queenside castling | enroque largo | O-O-O - towards a-file |
| development | desarrollo | Moving pieces to active squares |
| center control | control del centro | Dominating d4, d5, e4, e5 |
| opening | apertura | First phase of the game |
| middlegame | medio juego | After development complete |
| endgame | final | Last phase with reduced material |
| pawn structure | estructura de peones | Arrangement determining plans |
| passed pawn | peon pasado | No opposing pawns blocking promotion |
| isolated pawn | peon aislado | No pawns on adjacent files |
| doubled pawns | peones doblados | Two pawns on same file |
| backward pawn | peon retrasado | Behind adjacent pawns |
| pawn chain | cadena de peones | Connected diagonal pawns |
| outpost | casilla fuerte | Square safe from enemy pawns |
| fianchetto | fianchetto | Italian term; bishop on long diagonal |
| initiative | iniciativa | Having the attacking pressure |
| tempo | tiempo | A unit of time (one move) |

---

## Usage Examples

CORRECT: "La horquilla del caballo en c7 ataca la torre y la dama" (The knight fork on c7 attacks the rook and queen)

INCORRECT: "El tenedor del caballero en c7..." (Wrong terms: tenedor, caballero)

CORRECT: "Despues de 1.e4 e5 2.Cf3..." - Wait, notation should stay as "Nf3" not "Cf3"

CORRECT: "Despues de 1.e4 e5 2.Nf3 Nc6 3.Bc4, llegamos a la Apertura Italiana"

Remember: Notation is UNIVERSAL, terminology is translated.
"""


async def add_glossary_source_to_notebook(
    client: Any,
    notebook_id: str,
    target_lang: str = 'es'
) -> bool:
    """Add glossary source document to user's notebook.

    This function adds the chess terminology glossary as a source document
    to ensure the AI uses correct terminology when responding.

    Args:
        client: NotebookLM client instance
        notebook_id: ID of the notebook to add source to
        target_lang: Target language for glossary ('es' only supported)

    Returns:
        True if glossary was added successfully, False otherwise
    """
    if target_lang != 'es':
        # Only Spanish glossary implemented for now
        logger.debug(
            "Glossary not added - only Spanish supported",
            target_lang=target_lang,
            notebook_id=notebook_id
        )
        return False

    try:
        await client.sources.add_text(
            notebook_id,
            title="Chess Terminology Glossary",
            content=GLOSSARY_SOURCE_TEMPLATE
        )
        logger.info(
            "Glossary source added to notebook",
            notebook_id=notebook_id,
            target_lang=target_lang
        )
        return True
    except Exception as e:
        logger.error(
            "Failed to add glossary source",
            notebook_id=notebook_id,
            error=str(e)
        )
        return False
