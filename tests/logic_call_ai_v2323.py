from pathlib import Path
import sys, tempfile, wave, math, struct, ast

root=Path(sys.argv[1])
sys.path.insert(0,str(root))
sys.path.insert(0,str(root/'vendor'))

import aliyvo_call_ai as m

# Schema/pesos da documentacao do supervisor.
ev={
 "criterios":{
   "abordagem":{"nota":8.5,"justificativa":""},
   "tecnica_venda":{"nota":5.0,"justificativa":""},
   "fechamento":{"nota":9.0,"justificativa":""},
   "conhecimento_tecnico":{"nota":None,"justificativa":""},
 }
}
assert m._score_general(ev)==7.4, m._score_general(ev)
assert set(m.WEIGHTS)=={"abordagem","tecnica_venda","fechamento","conhecimento_tecnico"}
for key in ["dialogo","resultado","resumo","criterios","pontos_fortes","pontos_melhorar","momentos_chave","oportunidade_perdida","sentimento_cliente","dica_principal","proxima_acao","crm"]:
    assert key in m.EVAL_SCHEMA["required"],key

# Teste real do mixer: sistema stereo 48k + mic mono 44.1k => WAV mono 16k.
td=Path(tempfile.mkdtemp(prefix="aliyvo_call_ai_test_"))
loop=td/"loop.wav";mic=td/"mic.wav";out=td/"mixed.wav"

def write_tone(path,rate,channels,hz,secs=1.2):
    frames=int(rate*secs)
    with wave.open(str(path),"wb") as w:
        w.setnchannels(channels);w.setsampwidth(2);w.setframerate(rate)
        buf=bytearray()
        for i in range(frames):
            v=int(7000*math.sin(2*math.pi*hz*i/rate))
            for _ in range(channels):buf+=struct.pack("<h",v)
        w.writeframes(bytes(buf))

write_tone(loop,48000,2,440)
write_tone(mic,44100,1,660)
m.mix_wavs(loop,mic,out)
with wave.open(str(out),"rb") as w:
    assert w.getnchannels()==1
    assert w.getsampwidth()==2
    assert w.getframerate()==16000
    dur=w.getnframes()/w.getframerate()
    assert 1.1<dur<1.3,dur

# PyAudioWPatch precisa estar empacotado/importavel.
import pyaudiowpatch
assert hasattr(pyaudiowpatch.PyAudio,"get_default_wasapi_loopback")

# O main precisa estar realmente conectado ao modulo.
main=(root/"main.py").read_text(encoding="utf-8")
ast.parse(main)
assert 'ALIYVO_VERSION = "0.23.23"' in main
assert "from aliyvo_call_ai import AliyvoCallAIManager" in main
assert 'self.calls_ai_toggle=QPushButton("📞  Ligações IA")' in main
assert "self._call_ai_manager=AliyvoCallAIManager(self)" in main
assert "self._call_ai_manager.on_call_started(cur)" in main
assert "self._call_ai_manager.on_call_finished(_call_ai_meta)" in main

# Detector rapido e pipeline completo presentes.
src=(root/"aliyvo_call_ai.py").read_text(encoding="utf-8")
for needle in [
 "self._call_poll_timer.setInterval(1000)",
 "def _multipart_transcription",
 "gpt-4o-transcribe",
 "def evaluate_transcript",
 "def _apply_crm",
 "self.owner._crm_schedule_followup",
 "def show_dashboard",
 "def test_audio",
]:
    assert needle in src,needle

print("ALIYVO_CALL_AI_V2323_TESTS=OK")
