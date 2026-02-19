import { addSyncMethod } from "@slidev/client";
import { defineAppSetup } from "@slidev/types";
import {
	ConnectionStatusEnum,
	changeConnectionState,
	connectionStatus,
	getWsInstance,
	setWsInstance,
} from "./connectionState";

// プレゼンターモード判定: /presenter パスまたは ?presenter クエリで判定
const isPresenter =
	window.location.pathname.includes("/presenter") ||
	window.location.search.includes("presenter");
const role = isPresenter ? "presenter" : "viewer";
const SYNC_SERVER = `${window.location.origin.replace(/^http/, "ws")}/ws?role=${role}`;

let reconnectTimer: number | null = null;

export function connectWebSocket(onUpdate: (data: Partial<object>) => void): void {

	// 既存のタイマーをクリア
	if (reconnectTimer) {
		clearTimeout(reconnectTimer);
		reconnectTimer = null;
	}

	const ws = new WebSocket(SYNC_SERVER);
	setWsInstance(ws);

	ws.onopen = () => {
		changeConnectionState(ConnectionStatusEnum.Connected);
	};

	ws.onmessage = (event) => {
		try {
			if (connectionStatus.value === ConnectionStatusEnum.Connected) {
				const data = JSON.parse(event.data);
				onUpdate(data);
			}
		} catch (e) {
			console.error("Failed to parse sync message", e);
		}
	};

	ws.onclose = () => {
		// Disconnected状態の場合は自動再接続しない
		if (connectionStatus.value === ConnectionStatusEnum.Disconnected) {
			return;
		}

		changeConnectionState(ConnectionStatusEnum.Connecting);
		reconnectTimer = setTimeout(() => {
			reconnectTimer = null;
			connectWebSocket(onUpdate);
		}, 3000) as unknown as number;
	};
}

interface Sync {
	init: <State extends object>(
		channelKey: string,
		onUpdate: (data: Partial<State>) => void,
		state: State,
		persist?: boolean,
	) => ((state: State, updating?: boolean) => void) | undefined;
}

const websocketSync: Sync = {
	init(_channelKey, onUpdate, _state, persist) {
		if (persist) return undefined;

		connectWebSocket(onUpdate);

		return (state, updating) => {
            const ws = getWsInstance();
            if (!updating && ws?.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify(state));
            }
		};
	},
};

export default defineAppSetup(({ app }) => {
	addSyncMethod(websocketSync);
});
