/**
 * AudioWorklet processor for recording PCM. Runs on the audio thread.
 * Posts Float32 samples to the main thread via port.postMessage.
 */
class RecorderProcessor extends AudioWorkletProcessor {
  process(inputs, _outputs, _parameters) {
    const input = inputs[0];
    if (input && input.length > 0) {
      const channel = input[0];
      if (channel && channel.length > 0) {
        const copy = channel.slice();
        this.port.postMessage({ samples: copy }, [copy.buffer]);
      }
    }
    return true;
  }
}

registerProcessor("recorder-processor", RecorderProcessor);
