from aiogram.fsm.state import State, StatesGroup


class AddChannelStates(StatesGroup):
    waiting_for_username = State()


class SearchStates(StatesGroup):
    waiting_for_query = State()
