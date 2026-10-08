import asyncio
from media_session import MediaSessionReader
from protocol import state_message, volume_message, parse_command

async def test_volume():
    reader = MediaSessionReader()
    await reader.initialize()
    
    vol = reader.get_volume()
    print(f"Current system volume: {vol:.2f} ({int(vol*100)}%)")
    assert 0.0 <= vol <= 1.0, f"Volume out of bounds: {vol}"
    
    # Test setting volume
    success = reader.set_volume(vol)
    assert success, "set_volume failed"
    
    state = await reader.get_current_state()
    if state:
        assert "volume" in state, "State dictionary missing 'volume'"
        print(f"State volume: {state['volume']:.2f}")
        
        sm = state_message(state)
        assert sm.get("volume") == state["volume"], "state_message missing volume"
        print("state_message:", sm)
        
        vm = volume_message(state)
        assert vm.get("volume") == state["volume"], "volume_message missing volume"
        assert vm.get("type") == "volume", "volume_message wrong type"
        print("volume_message:", vm)
        
    cmd = parse_command('{"type": "command", "action": "volume", "level": 0.65}')
    assert cmd["action"] == "volume", "Failed to parse volume action"
    assert cmd["level"] == 0.65, "Failed to parse volume level"
    print("Parsed command:", cmd)
    
    print("\nALL VOLUME PROTOCOL TESTS PASSED!")

if __name__ == "__main__":
    asyncio.run(test_volume())
