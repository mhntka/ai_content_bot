import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, User, Chat

import handlers
from states import ChannelStates

@pytest.fixture
def mock_message():
    msg = MagicMock(spec=Message)
    msg.from_user = User(id=123, is_bot=False, first_name="Test")
    msg.text = "Test text"
    msg.chat = Chat(id=123, type="private")
    msg.answer = AsyncMock()
    return msg

@pytest.fixture
def mock_callback():
    cb = MagicMock(spec=CallbackQuery)
    cb.from_user = User(id=123, is_bot=False, first_name="Test")
    cb.message = MagicMock(spec=Message)
    cb.message.answer = AsyncMock()
    cb.answer = AsyncMock()
    return cb

@pytest.fixture
def mock_state():
    state = MagicMock(spec=FSMContext)
    state.get_state = AsyncMock()
    state.clear = AsyncMock()
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()
    state.get_data = AsyncMock()
    return state

@pytest.mark.asyncio
async def test_cmd_cancel_in_state(mock_message, mock_state):
    """Тест команды cancel когда пользователь в состоянии"""
    mock_state.get_state.return_value = "some_state"
    
    await handlers.cmd_cancel(mock_message, mock_state)
    
    mock_state.clear.assert_called_once()
    mock_message.answer.assert_called_with("✖️ Отменено", reply_markup=handlers.get_main_reply_keyboard())

@pytest.mark.asyncio
async def test_cmd_cancel_no_state(mock_message, mock_state):
    """Тест команды cancel когда нет активного действия"""
    mock_state.get_state.return_value = None
    
    await handlers.cmd_cancel(mock_message, mock_state)
    
    mock_state.clear.assert_not_called()
    mock_message.answer.assert_called_with("📭 Нет активного действия")

@pytest.mark.asyncio
@patch('handlers.get_user_channels', new_callable=AsyncMock)
async def test_cb_add_channel_under_limit(mock_get_channels, mock_callback, mock_state):
    """Тест нажатия кнопки добавления канала (меньше лимита)"""
    mock_get_channels.return_value = [1, 2] # 2 channels
    mock_callback.data = "add_channel"
    
    await handlers.cb_add_channel(mock_callback, mock_state)
    
    mock_state.set_state.assert_called_with(ChannelStates.waiting_for_name)
    mock_callback.message.answer.assert_called()

@pytest.mark.asyncio
@patch('handlers.get_user_channels', new_callable=AsyncMock)
async def test_cb_add_channel_over_limit(mock_get_channels, mock_callback, mock_state):
    """Тест нажатия кнопки добавления канала (лимит превышен)"""
    mock_get_channels.return_value = [1, 2, 3, 4, 5] # 5 channels
    mock_callback.data = "add_channel"
    
    await handlers.cb_add_channel(mock_callback, mock_state)
    
    mock_state.set_state.assert_not_called()
    mock_callback.answer.assert_called_with("❌ Достигнут лимит (5 каналов).", show_alert=True)
