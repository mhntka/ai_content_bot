from aiogram.fsm.state import State, StatesGroup

class ChannelStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_id = State()

class SourceStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_url = State()
    waiting_for_keywords = State()

class DraftStates(StatesGroup):
    waiting_for_text = State()
