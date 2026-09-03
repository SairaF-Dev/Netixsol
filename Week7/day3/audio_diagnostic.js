// Copy and paste this into your browser console (F12) to diagnose audio issues

(function() {
    console.log("=== SARA AUDIO DIAGNOSTICS ===\n");
    
    // 1. Find the audio element
    const audio = document.getElementById('assistantAudio');
    console.log("1. Audio Element:", audio ? "✅ Found" : "❌ Not found");
    
    if (audio) {
        console.log("   - muted:", audio.muted);
        console.log("   - volume:", audio.volume);
        console.log("   - src:", audio.src ? "✅ Has source" : "❌ No source");
        console.log("   - canPlayType('audio/mpeg'):", audio.canPlayType('audio/mpeg'));
        console.log("   - readyState:", audio.readyState, "(0=not started, 1=loading, 2=loaded, 3=playing, 4=done)");
        console.log("   - networkState:", audio.networkState, "(0=empty, 1=idle, 2=loading, 3=no source)");
    }
    
    // 2. Check MediaSource
    console.log("\n2. MediaSource API:", typeof MediaSource !== 'undefined' ? "✅ Available" : "❌ Not available");
    if (typeof MediaSource !== 'undefined') {
        console.log("   - MP3 support:", MediaSource.isTypeSupported('audio/mpeg'));
    }
    
    // 3. Check browser audio context
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    console.log("\n3. AudioContext:", audioCtx ? "✅ Available" : "❌ Not available");
    if (audioCtx) {
        console.log("   - State:", audioCtx.state, "(suspended/running/closed)");
        console.log("   - Sample rate:", audioCtx.sampleRate);
    }
    
    // 4. FIX: Unmute audio
    if (audio) {
        console.log("\n4. FIXING AUDIO...");
        audio.muted = false;
        audio.volume = 1.0;
        console.log("   ✅ Audio unmuted");
        console.log("   ✅ Volume set to 100%");
    }
    
    // 5. Check if audio events are firing
    console.log("\n5. Adding audio event listeners...");
    if (audio) {
        audio.addEventListener('play', () => console.log("   🔊 PLAY event fired"));
        audio.addEventListener('pause', () => console.log("   ⏸ PAUSE event fired"));
        audio.addEventListener('error', (e) => console.log("   ❌ ERROR:", audio.error?.message));
        audio.addEventListener('ended', () => console.log("   ✅ ENDED event fired"));
        console.log("   ✅ Listeners attached");
    }
    
    // 6. Try to play a test
    console.log("\n6. Testing playback...");
    if (audio && audio.src) {
        audio.play()
            .then(() => console.log("   ✅ Play succeeded!"))
            .catch(err => console.log("   ❌ Play failed:", err.message));
    }
    
    console.log("\n=== END DIAGNOSTICS ===\n");
    console.log("If audio still doesn't play:");
    console.log("1. Check your system volume 🔊");
    console.log("2. Check browser tab isn't muted (speaker icon in tab)");
    console.log("3. Try a different browser");
    console.log("4. Check if audio device is working");
})();
