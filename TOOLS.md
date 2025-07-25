wget https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp
./yt-dlp --update-to nightly
./yt-dlp -x --audio-format mp3 "https://www.youtube.com/watch?v=53M-CvfEDmg"



git clone https://github.com/ggml-org/whisper.cpp.git
Navigate into the directory:

cd whisper.cpp
Then, download one of the Whisper models converted in ggml format. For example:

#sh ./models/download-ggml-model.sh base.en
sh ./models/download-ggml-model.sh small
Now build the whisper-cli example and transcribe an audio file like this:

# build the project
cmake -B build
cmake --build build -j --config Release

# transcribe an audio file
./build/bin/whisper-cli -f samples/jfk.wav
https://github.com/ggml-org/whisper.cpp/

./whisper.cpp/build/bin/whisper-cli -m ./whisper.cpp/models/ggml-small.bin  -l ru --output-txt -f ./АПТИ\ И\ ШТУРМ\ ЛУГАНСКОГО\ БАССЕЙНА.\ Z-военблогеры\ уничтожили\ Алаудинова\ и\ требуют\ расправы\ \[53M-CvfEDmg\].mp3

brew install llama.cpp
export HF_TOKEN=hf_

llama-cli -hf google/gemma-2b-GGUF