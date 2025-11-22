# from aqt.utils import showInfo
# from aqt import gui_hooks

# def myfunc(card):
#   print(f"question shown, card question is: {card.q()}")

# gui_hooks.reviewer_did_show_question.append(myfunc)

from typing import Optional

from anki.cards import Card
from aqt import mw, gui_hooks
from aqt.utils import showInfo, qconnect
from aqt.qt import QAction, QTimer

DEFAULT_SECONDS = 6.0
TIMER_FIELD_NAME = "Timer"

auto_answer_enabled: bool = True
_timer: Optional[QTimer] = None
_current_card_id: Optional[int] = None


def _cancel_timer() -> None:
    """Stop and dispose of any existing timer."""
    global _timer
    if _timer is not None:
        _timer.stop()
        _timer.deleteLater()
        _timer = None

def _schedule_auto_answer(card: Card) -> None:
    """
    Called when the reviewer shows the QUESTION side.
    Schedules an automatic 'show answer' after N seconds.
    """
    global _timer, _current_card_id
    print("Auto answer starts")

    _cancel_timer()

    if not auto_answer_enabled:
        print("Auto answer is disabled")
        return

    if mw.reviewer.state != "question":
        print("What is this?")
        return


    seconds = DEFAULT_SECONDS

    note = card.note()
    if TIMER_FIELD_NAME in note:
        raw_value = note[TIMER_FIELD_NAME].strip()
        if raw_value:
            try:
                seconds = float(raw_value)
            except ValueError:
                # Invalid value, just fall back to default
                pass

    _current_card_id = card.id

    _timer = QTimer(mw)
    _timer.setSingleShot(True)

    print(f"Auto answer will be shown in {seconds} seconds")

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
            # Private method, but standard in add-ons
            mw.reviewer.onEnterKey()

    _timer.timeout.connect(on_timeout)
    _timer.start(int(seconds * 1000))

def _on_show_answer(card: Card) -> None:
    """When the answer shows, we cancel the timer (nothing left to do)."""
    _cancel_timer()
    print("Answer shown, timer cancelled")

def _toggle_auto_answer() -> None:
    """Menu action to turn the feature on/off."""
    global auto_answer_enabled
    auto_answer_enabled = not auto_answer_enabled
    status = "ON" if auto_answer_enabled else "OFF"
    showInfo(f"Per-card auto answer is now {status}.")

def _setup_menu() -> None:
    """Add a menu item under Tools to toggle the behavior."""
    action = QAction("Toggle Per-Card Auto Answer", mw)
    qconnect(action.triggered, _toggle_auto_answer)
    mw.form.menuTools.addAction(action)

gui_hooks.reviewer_did_show_question.append(_schedule_auto_answer)
gui_hooks.reviewer_did_show_answer.append(_on_show_answer)
gui_hooks.main_window_did_init.append(lambda: _setup_menu())