<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const videoRef = ref<HTMLVideoElement | null>(null)
const isLoading = ref(true)
const hasError = ref(false)
const errorMessage = ref('')

let stage: any = null

const isDev = import.meta.env.DEV
const SDK_URL = 'https://web-broadcast.live-video.net/1.32.0/amazon-ivs-web-broadcast.js'
const PARTICIPANT_TOKEN = import.meta.env.VITE_IVS_PARTICIPANT_TOKEN || ''

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if ((window as any).IVSBroadcastClient) {
      resolve()
      return
    }
    const script = document.createElement('script')
    script.src = src
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('Failed to load IVS Web Broadcast SDK'))
    document.head.appendChild(script)
  })
}

async function initStage() {
  if (isDev) {
    isLoading.value = false
    return
  }

  if (!PARTICIPANT_TOKEN) {
    hasError.value = true
    errorMessage.value = '参加トークンが設定されていません'
    isLoading.value = false
    return
  }

  try {
    await loadScript(SDK_URL)

    const {
      Stage,
      SubscribeType,
      StageEvents,
    } = (window as any).IVSBroadcastClient

    const strategy = {
      stageStreamsToPublish: () => [],
      shouldPublishParticipant: () => false,
      shouldSubscribeToParticipant: () => SubscribeType.AUDIO_VIDEO,
    }

    stage = new Stage(PARTICIPANT_TOKEN, strategy)

    stage.on(
      StageEvents.STAGE_PARTICIPANT_STREAMS_ADDED,
      (participant: any, streams: any[]) => {
        if (participant.isLocal) return

        const mediaStream = new MediaStream()
        streams.forEach((stream: any) => {
          mediaStream.addTrack(stream.mediaStreamTrack)
        })

        if (videoRef.value) {
          videoRef.value.muted = true
          videoRef.value.srcObject = mediaStream
          videoRef.value.play().catch(() => {})
        }
        isLoading.value = false
      }
    )

    stage.on(
      StageEvents.STAGE_PARTICIPANT_STREAMS_REMOVED,
      (_participant: any) => {
        if (videoRef.value) {
          videoRef.value.srcObject = null
        }
      }
    )

    stage.on(StageEvents.STAGE_PARTICIPANT_LEFT, () => {
      if (videoRef.value) {
        videoRef.value.srcObject = null
      }
    })

    await stage.join()
    isLoading.value = false
  } catch (err) {
    hasError.value = true
    errorMessage.value = 'ステージへの接続に失敗しました'
    isLoading.value = false
    console.error('IVS Stage init error:', err)
  }
}

onMounted(() => {
  initStage()
})

onUnmounted(() => {
  if (stage) {
    stage.leave()
    stage = null
  }
})
</script>

<template>
  <div class="ivs-container">
    <template v-if="isDev">
      <div class="ivs-mock">
        <div class="ivs-mock-icon">▶</div>
        <p>IVS Live Stream (DEV MOCK)</p>
      </div>
    </template>
    <template v-else>
      <div v-if="isLoading && !hasError" class="ivs-loading">
        <div class="ivs-spinner" />
        <p>配信を読み込み中...</p>
      </div>
      <div v-if="hasError" class="ivs-error">
        <p>{{ errorMessage }}</p>
      </div>
      <video
        ref="videoRef"
        playsinline
        autoplay
        class="ivs-video"
      />
    </template>
  </div>
</template>

<style scoped>
.ivs-container {
  position: absolute;
  inset: 0;
  overflow: hidden;
  background: #000;
}

.ivs-video {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
  background: #000;
}

.ivs-mock {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #1a1a2e;
  border: 2px dashed rgba(78, 201, 176, 0.4);
}

.ivs-mock-icon {
  font-size: 4rem;
  color: #4ec9b0;
  margin-bottom: 1rem;
}

.ivs-mock p {
  font-size: 1.2rem !important;
  color: #4ec9b0;
  opacity: 0.8;
}

.ivs-loading {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #000;
  z-index: 10;
}

.ivs-loading p {
  font-size: 1rem !important;
  color: #4ec9b0;
  margin-top: 1rem;
}

.ivs-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(78, 201, 176, 0.2);
  border-top-color: #4ec9b0;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.ivs-error {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
  z-index: 10;
}

.ivs-error p {
  font-size: 1rem !important;
  color: #ff6b6b;
}
</style>
