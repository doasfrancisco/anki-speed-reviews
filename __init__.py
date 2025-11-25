from typing import Optional, Dict
import json
import os
import copy

from anki.cards import Card
from aqt import mw, gui_hooks
from aqt.utils import showInfo, qconnect, getText
from aqt.qt import QAction, QTimer, QElapsedTimer

# ===== Config =====
auto_answer_enabled: bool = True
_timer: Optional[QTimer] = None
_elapsed_timer: Optional[QElapsedTimer] = None
_current_card_id: Optional[int] = None


ADDON_DIR = os.path.dirname(__file__)
USER_FILES_DIR = os.path.join(ADDON_DIR, "user_files")
TIMERS_PATH = os.path.join(USER_FILES_DIR, "timers.json")

_timers: Dict[str, dict] = {}
_show_timer: Optional[float] = None


def _load_timers() -> None:
    """Load timers.json into _timers dict."""
    global _timers
    if os.path.exists(TIMERS_PATH):
        try:
            with open(TIMERS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            _timers = data.get("timers", {})
        except Exception as e:
            print("AutoAnswerTimer: failed to load timers.json:", e)
            _timers = {}
    else:
        _timers = {}

def _save_timers() -> None:
    """Persist _timers dict to timers.json."""
    data = {"timers": _timers}
    try:
        with open(TIMERS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("AutoAnswerTimer: failed to save timers.json:", e)

_load_timers()


def _cancel_timer() -> None:
    """Stop and dispose of any existing timer."""
    global _timer
    if _timer is not None:
        _timer.stop()
        _timer.deleteLater()
        _timer = None

def _cancel_review() -> None:
    global _elapsed_timer, _show_timer
    _elapsed_timer = None
    _show_timer = None
    _cancel_timer()


def _get_card_info(card_id: int) -> dict:
    """Return timer info for this card, from JSON or default."""
    try:
        return _timers.get(str(card_id), {})
    except (TypeError, ValueError):
        return {}


def _on_show_question(card: Card) -> None:
    global _timer, _elapsed_timer, _current_card_id

    _cancel_timer()

    if not auto_answer_enabled:
        print("Auto answer is disabled")
        return

    if mw.reviewer.state != "question":
        print("Not in question state, skipping")
        return

    _current_card_id = card.id
    card_timer = _get_card_info(_current_card_id).get("timer", 0)

    _elapsed_timer = QElapsedTimer()
    _elapsed_timer.start()

    if card_timer == 0:
        return

    _timer = QTimer(mw)
    _timer.setSingleShot(True)

    print(f"Auto answer will be shown in {card_timer} seconds")

    def on_timeout() -> None:
        print("Auto answer timer fired")
        # Only act if:
        #  - reviewer still exists
        #  - we're still on the same card
        #  - still on question side (haven't shown answer yet)
        if (
            mw.reviewer is not None
            and mw.reviewer.card is not None
            and mw.reviewer.card.id == _current_card_id
            and mw.reviewer.state == "question"
        ):
            mw.reviewer.onEnterKey()  # simulate pressing space/enter

    _timer.timeout.connect(on_timeout)
    _timer.start(card_timer)

def _on_show_answer(card: Card) -> None:
    global _elapsed_timer, _show_timer

    _cancel_timer()
    print("Answer shown, timer cancelled")

    if not auto_answer_enabled:
        print("Auto answer is disabled")
        return

    _show_timer = _elapsed_timer.elapsed()
    print(f"How long it took to show the answer: {_show_timer / 1000} seconds")

def _on_answer_card(reviewer, card: Card, ease) -> None:
    global _timers, _show_timer

    _current_card_id = card.id
    card_info = _get_card_info(_current_card_id)
    card_timer = card_info.get("timer", 0)
    streak = card_info.get("streak", 0)
    wrong_counter = card_info.get("wrong_counter", 0)

    if card_timer == 0:
        if ease > 1:
            card_timer = _show_timer
            print("First timer for card set")
    elif _show_timer < card_timer and ease > 1:
        card_timer = _show_timer
        streak = 0
        wrong_counter = 0
        print(f"Timer for card updated to {card_timer / 1000} seconds")
    elif ease > 1:
        wrong_counter = 0
        streak += 1
        if streak > 1:
            card_timer -= 1000
            streak = 0
    elif ease == 1:
        streak = 0
        wrong_counter += 1
        if wrong_counter > 1:
            card_timer += 1000
            wrong_counter = 0

    _timers[str(_current_card_id)] = {"timer": card_timer, "streak": streak, "wrong_counter": wrong_counter}
    _save_timers()

def _on_state_change(new_state, old_state) -> None:
    if old_state == "review":
        _cancel_review()
        print(f"State changed from {old_state} to {new_state}")

# ===== UI =====

def _toggle_auto_answer() -> None:
    """Menu action to turn the feature on/off."""
    global auto_answer_enabled
    auto_answer_enabled = not auto_answer_enabled
    status = "ON" if auto_answer_enabled else "OFF"
    showInfo(f"Per-card auto answer is now {status}.")

def _setup_menu() -> None:
    """Add menu items under Tools."""
    action_toggle = QAction("Toggle Per-Card Auto Answer", mw)
    qconnect(action_toggle.triggered, _toggle_auto_answer)
    mw.form.menuTools.addAction(action_toggle)


def _set_timer_for_current_card() -> None:
    """Ask user for seconds and store them for the current card in timers.json."""
    global _timers

    if mw.reviewer is None or mw.reviewer.card is None:
        showInfo("No card is currently being reviewed.")
        return

    card = mw.reviewer.card
    card_id = str(card.id)

    current = _timers.get(card_id)
    default_str = str(current if current is not None else "")

    text, ok = getText(
        "Enter auto-answer delay in seconds for this card.\n"
        "(Leave empty to cancel, or set 0 to disable for this card.)",
        default=default_str,
        title="Set Auto-Answer Timer",
    )

    if not ok:
        return

    text = text.strip()
    if not text:
        prev_set = card_id in _timers
        del _timers[card_id]
        _save_timers()
        if prev_set:
            showInfo("Custom timer cleared for this card.")
        return

    try:
        seconds = float(text)
    except ValueError:
        showInfo("Invalid number. Please enter a valid numeric value.")
        return
    
    if seconds < 0:
        showInfo("Invalid number. Please enter a valid numeric value.")
        return

    if seconds == 0:
        prev_set = card_id in _timers
        del _timers[card_id]
        _save_timers()
        if prev_set:
            showInfo("Custom timer cleared for this card.")
        return
    else:
        _timers[card_id] = seconds
        _save_timers()
        showInfo(f"Timer for this card set to {seconds} seconds.")

def _add_reviewer_more_menu_options(reviewer, menu):
    """Adds 'Set Timer' into the More menu."""
    action_set = QAction("Set Auto-Answer Timer for This Card", menu)
    qconnect(action_set.triggered, _set_timer_for_current_card)
    menu.addAction(action_set)



gui_hooks.main_window_did_init.append(lambda: _setup_menu())
gui_hooks.reviewer_will_show_context_menu.append(_add_reviewer_more_menu_options)

gui_hooks.reviewer_did_show_question.append(_on_show_question)
gui_hooks.reviewer_did_show_answer.append(_on_show_answer)
gui_hooks.reviewer_did_answer_card.append(_on_answer_card)

gui_hooks.state_did_change.append(_on_state_change)