import { useRef } from 'react';
import { useAppDispatch } from '../store/store';
import { setSSEConnected, setSSELastEvent, setVehicle, updateLogRecords } from '@src/store/actions';
import { API_BASE_URL } from '@src/services/proxy';

export const useSSE = () => {
  const url = `${API_BASE_URL}/sse`;
  const dispatch = useAppDispatch();
  const eventSourceRef = useRef<EventSource | null>(null);

  const connect = (pid: string) => {
    if (eventSourceRef.current) {
      return;
    }
    const eventSource = new EventSource(`${url}?pid=${pid}`);

    eventSource.onopen = () => {
      dispatch(setSSEConnected(true));
    };

    eventSource.onmessage = (event) => {
      try {
        const action = JSON.parse(event.data.replace(/'/g, '"'));
        dispatch(setSSELastEvent(action));
        switch (action.type) {
          case 'vehicle':
            dispatch(setVehicle(action.data));
            break;
          case 'log':
            dispatch(updateLogRecords(action.data));
            break;
          default:
            break;
        }
      } catch (error) {
        console.error('Failed to parse SSE event:', error);
      }
    };

    eventSource.onerror = () => {
      disconnect();
    };

    eventSourceRef.current = eventSource;
  };

  const disconnect = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      dispatch(setSSEConnected(false));
      window.localStorage.clear();
    }
};

  return {
    connect,
    disconnect,
  };
};