from resemblyzer import VoiceEncoder, preprocess_wav
import numpy as np
import io
import librosa
import streamlit as st


@st.cache_resource
def load_voice_encoder():
    return VoiceEncoder()

def get_voice_embedding(audio_bytes):
    try:
        encoder = load_voice_encoder()
        audio,sr = librosa.load(io.BytesIO(audio_bytes),sr=16000)
        wav = preprocess_wav(audio)
        embedding = encoder.embed_utterance(wav)
        return embedding.tolist()
    except Exception as e:
        st.error('voice recog error')
        return None




def identify_speaker(new_embedding, candidates_dict, threshold=0.65):
    if new_embedding is None or not candidates_dict:
        return None, 0.0

    best_sid = None
    best_score = -1.0

    for sid, stored_encodding in candidates_dict.items():
        if stored_encodding:
            similarity = np.dot(new_embedding, stored_encodding)   # ✅ fixed
            if similarity > best_score:
                best_score = similarity
                best_sid = sid

    if best_score >= threshold:
        return best_sid, best_score

    return None, best_score

def process_bulk_audio(audio_bytes, candidates_dict, threshold=0.05):
    try:
        encoder = load_voice_encoder()

        audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=16000)
        segments = librosa.effects.split(audio, top_db=30)
        identifield_results = {}
        for start, end in segments:
            if (end - start) < sr * 0.5:
                continue
            segment_audio = audio[start:end]
            wav = preprocess_wav(segment_audio)
            embedding = encoder.embed_utterance(wav)

            sid, score = identify_speaker(embedding, candidates_dict, threshold)
            if sid:
                if sid not in identifield_results or score > identifield_results[sid]:
                    identifield_results[sid] = score

        return identifield_results
    except Exception as e:
        import traceback
        traceback.print_exc()
        st.error(f'Bulk process error: {e}')
        return {}



