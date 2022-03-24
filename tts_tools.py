import time

start = time.time()

import tensorflow as tf

import os

import numpy as np
import matplotlib.pyplot as plt

from pydub import AudioSegment
import soundfile as sf

from tensorflow_tts.inference import TFAutoModel
from tensorflow_tts.inference import AutoProcessor

tacotron2 = TFAutoModel.from_pretrained("tensorspeech/tts-tacotron2-baker-ch", name="tacotron2")
fastspeech2 = TFAutoModel.from_pretrained("tensorspeech/tts-fastspeech2-baker-ch", name="fastspeech2")
mb_melgan = TFAutoModel.from_pretrained("tensorspeech/tts-mb_melgan-baker-ch", name="mb_melgan")
processor = AutoProcessor.from_pretrained("tensorspeech/tts-tacotron2-baker-ch")


def do_synthesis(input_text, text2mel_model, vocoder_model, text2mel_name, vocoder_name):
    input_ids = processor.text_to_sequence(input_text, inference=True)

    # text2mel part
    if text2mel_name == "TACOTRON":
        _, mel_outputs, stop_token_prediction, alignment_history = text2mel_model.inference(
            tf.expand_dims(tf.convert_to_tensor(input_ids, dtype=tf.int32), 0),
            tf.convert_to_tensor([len(input_ids)], tf.int32),
            tf.convert_to_tensor([0], dtype=tf.int32)
        )
    elif text2mel_name == "FASTSPEECH2":
        mel_before, mel_outputs, duration_outputs, _, _ = text2mel_model.inference(
            tf.expand_dims(tf.convert_to_tensor(input_ids, dtype=tf.int32), 0),
            speaker_ids=tf.convert_to_tensor([0], dtype=tf.int32),
            speed_ratios=tf.convert_to_tensor([1.0], dtype=tf.float32),
            f0_ratios=tf.convert_to_tensor([1.0], dtype=tf.float32),
            energy_ratios=tf.convert_to_tensor([1.0], dtype=tf.float32),
        )
    else:
        raise ValueError("Only TACOTRON, FASTSPEECH2 are supported on text2mel_name")

    # vocoder part
    if vocoder_name == "MB-MELGAN":
        # tacotron-2 generate noise in the end symtematic, let remove it :v.
        if text2mel_name == "TACOTRON":
            remove_end = 1024
        else:
            remove_end = 1
        audio = vocoder_model.inference(mel_outputs)[0, :-remove_end, 0]
    else:
        raise ValueError("Only MB_MELGAN are supported on vocoder_name")

    if text2mel_name == "TACOTRON":
        return mel_outputs.numpy(), alignment_history.numpy(), audio.numpy()
    else:
        return mel_outputs.numpy(), audio.numpy()


def visualize_attention(alignment_history):
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111)
    ax.set_title(f'Alignment steps')
    im = ax.imshow(
        alignment_history,
        aspect='auto',
        origin='lower',
        interpolation='none')
    fig.colorbar(im, ax=ax)
    xlabel = 'Decoder timestep'
    plt.xlabel(xlabel)
    plt.ylabel('Encoder timestep')
    plt.tight_layout()
    plt.show()
    plt.close()


def visualize_mel_spectrogram(mels):
    mels = tf.reshape(mels, [-1, 80]).numpy()
    fig = plt.figure(figsize=(10, 8))
    ax1 = fig.add_subplot(311)
    ax1.set_title(f'Predicted Mel-after-Spectrogram')
    im = ax1.imshow(np.rot90(mels), aspect='auto', interpolation='none')
    fig.colorbar(mappable=im, shrink=0.65, orientation='horizontal', ax=ax1)
    plt.show()
    plt.close()


def create_audio(text, output_path='.'):
    t0 = time.time()
    _, _, audios = do_synthesis(text, tacotron2, mb_melgan, "TACOTRON", "MB-MELGAN")
    # _, audios = do_synthesis(text, fastspeech2, mb_melgan, "FASTSPEECH2", "MB-MELGAN")

    mp3_file = '{path}/{text}.{extension}'.format(path=output_path, text=text, extension='mp3')
    wav_file = '{path}/{text}.{extension}'.format(path=output_path, text=text, extension='wav')

    sf.write(wav_file, audios, 24000, 'PCM_24')
    AudioSegment.from_file(
        wav_file,
        format="wav"
    ).export(
        mp3_file, format="mp3", bitrate="192k"
    )

    os.remove(wav_file)

    print(time.time() - t0)


if __name__ == '__main__':
    input_text = "着急"

    create_audio(input_text)
    create_audio('你好')

    print(time.time() - start)
    exit()
    # setup window for tacotron2 if you want to try
    tacotron2.setup_window(win_front=20, win_back=20)

    mels, alignment_history, taco_audios = do_synthesis(input_text, tacotron2, mb_melgan, "TACOTRON", "MB-MELGAN")
    # visualize_attention(alignment_history[0])
    # visualize_mel_spectrogram(mels[0])
    # ipd.Audio(taco_audios, rate=24000)

    sf.write('%s.wav' % input_text, taco_audios, 24000, 'PCM_24')
    wav_audio = AudioSegment.from_file('%s.wav' % input_text, format="wav")
    wav_audio.export("%s.mp3" % input_text, format="mp3", bitrate="192k")
