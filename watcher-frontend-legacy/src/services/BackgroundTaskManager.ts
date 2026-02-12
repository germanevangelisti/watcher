/**
 * Background Task Manager
 * Gestiona la ejecución de workflows en background y actualiza el estado en tiempo real
 */

export interface BackgroundTask {
  id: string;
  workflow_id: string;
  workflow_name: string;
  workflow_type: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  progress: number;
  total_tasks: number;
  completed_tasks: number;
  started_at: Date;
  completed_at?: Date;
  error_message?: string;
}

type TaskUpdateCallback = (tasks: BackgroundTask[]) => void;

class BackgroundTaskManagerClass {
  private tasks: Map<string, BackgroundTask> = new Map();
  private listeners: Set<TaskUpdateCallback> = new Set();
  private ws: WebSocket | null = null;
  private reconnectInterval: number = 5000;
  private reconnectTimer: NodeJS.Timeout | null = null;

  constructor() {
    // WebSocket deshabilitado temporalmente - usando polling en su lugar
    // Descomentar cuando se implemente el endpoint WebSocket en el backend
    // this.connectWebSocket();
  }

  /**
   * Conecta al WebSocket para recibir updates en tiempo real
   * NOTA: Actualmente deshabilitado - el sistema usa polling
   */
  private connectWebSocket() {
    // Solo intentar conectar si está en browser
    if (typeof window === 'undefined') return;
    
    try {
      this.ws = new WebSocket('ws://localhost:8001/api/v1/ws');

      this.ws.onopen = () => {
        console.log('✅ WebSocket conectado');
        if (this.reconnectTimer) {
          clearTimeout(this.reconnectTimer);
          this.reconnectTimer = null;
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleWebSocketMessage(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.warn('⚠️ WebSocket error (backend may not be running):', error.type);
      };

      this.ws.onclose = () => {
        console.log('🔌 WebSocket desconectado, reintentando en 10s...');
        // Intentar reconectar menos frecuentemente
        this.reconnectTimer = setTimeout(() => {
          this.connectWebSocket();
        }, 10000); // 10 segundos en lugar de 5
      };
    } catch (error) {
      console.warn('⚠️ No se pudo conectar WebSocket (backend offline)');
      // Reconectar después de más tiempo si hay error
      this.reconnectTimer = setTimeout(() => {
        this.connectWebSocket();
      }, 15000);
    }
  }

  /**
   * Maneja mensajes del WebSocket
   */
  private handleWebSocketMessage(data: any) {
    const { event, workflow_id, workflow_name, status, progress, message } = data;

    if (event === 'workflow_started') {
      this.addTask({
        id: workflow_id,
        workflow_id,
        workflow_name: workflow_name || 'Análisis sin nombre',
        workflow_type: data.workflow_type || 'unknown',
        status: 'in_progress',
        progress: 0,
        total_tasks: data.total_tasks || 0,
        completed_tasks: 0,
        started_at: new Date()
      });
    } else if (event === 'task_completed' || event === 'workflow_progress') {
      this.updateTaskProgress(workflow_id, progress || 0, data.completed_tasks || 0);
    } else if (event === 'workflow_completed') {
      this.completeTask(workflow_id);
    } else if (event === 'workflow_failed') {
      this.failTask(workflow_id, message || 'Error desconocido');
    }
  }

  /**
   * Agrega una tarea al manager
   */
  addTask(task: BackgroundTask) {
    this.tasks.set(task.id, task);
    this.notifyListeners();
    console.log(`📝 Tarea agregada: ${task.workflow_name}`);
  }

  /**
   * Actualiza el progreso de una tarea
   */
  updateTaskProgress(taskId: string, progress: number, completed_tasks?: number) {
    const task = this.tasks.get(taskId);
    if (task) {
      task.progress = Math.min(progress, 100);
      task.status = 'in_progress';
      if (completed_tasks !== undefined) {
        task.completed_tasks = completed_tasks;
      }
      this.tasks.set(taskId, task);
      this.notifyListeners();
    }
  }

  /**
   * Marca una tarea como completada
   */
  completeTask(taskId: string) {
    const task = this.tasks.get(taskId);
    if (task) {
      task.status = 'completed';
      task.progress = 100;
      task.completed_at = new Date();
      this.tasks.set(taskId, task);
      this.notifyListeners();
      console.log(`✅ Tarea completada: ${task.workflow_name}`);

      // Mostrar notificación
      this.showNotification(
        '✅ Análisis Completado',
        `${task.workflow_name} ha finalizado exitosamente`,
        'success'
      );

      // Remover después de 10 segundos
      setTimeout(() => {
        this.removeTask(taskId);
      }, 10000);
    }
  }

  /**
   * Marca una tarea como fallida
   */
  failTask(taskId: string, error: string) {
    const task = this.tasks.get(taskId);
    if (task) {
      task.status = 'failed';
      task.error_message = error;
      task.completed_at = new Date();
      this.tasks.set(taskId, task);
      this.notifyListeners();
      console.error(`❌ Tarea fallida: ${task.workflow_name} - ${error}`);

      // Mostrar notificación
      this.showNotification(
        '❌ Análisis Fallido',
        `${task.workflow_name}: ${error}`,
        'error'
      );

      // Remover después de 15 segundos
      setTimeout(() => {
        this.removeTask(taskId);
      }, 15000);
    }
  }

  /**
   * Remueve una tarea
   */
  removeTask(taskId: string) {
    this.tasks.delete(taskId);
    this.notifyListeners();
  }

  /**
   * Obtiene todas las tareas activas
   */
  getActiveTasks(): BackgroundTask[] {
    return Array.from(this.tasks.values()).filter(
      task => task.status === 'in_progress' || task.status === 'pending'
    );
  }

  /**
   * Obtiene todas las tareas
   */
  getAllTasks(): BackgroundTask[] {
    return Array.from(this.tasks.values());
  }

  /**
   * Obtiene una tarea por ID
   */
  getTask(taskId: string): BackgroundTask | undefined {
    return this.tasks.get(taskId);
  }

  /**
   * Suscribe un listener para recibir updates
   */
  subscribe(callback: TaskUpdateCallback): () => void {
    this.listeners.add(callback);
    // Retornar función para desuscribir
    return () => {
      this.listeners.delete(callback);
    };
  }

  /**
   * Notifica a todos los listeners
   */
  private notifyListeners() {
    const tasks = this.getAllTasks();
    this.listeners.forEach(listener => {
      try {
        listener(tasks);
      } catch (error) {
        console.error('Error in listener:', error);
      }
    });
  }

  /**
   * Muestra una notificación del navegador
   */
  private showNotification(title: string, body: string, type: 'success' | 'error' | 'info') {
    // Mostrar notificación en el navegador si está permitido
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification(title, {
        body,
        icon: type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'
      });
    }

    // También disparar evento personalizado para notificaciones en la UI
    window.dispatchEvent(
      new CustomEvent('task-notification', {
        detail: { title, body, type }
      })
    );
  }

  /**
   * Solicita permisos de notificación
   */
  async requestNotificationPermission() {
    if ('Notification' in window && Notification.permission === 'default') {
      const permission = await Notification.requestPermission();
      return permission === 'granted';
    }
    return Notification.permission === 'granted';
  }

  /**
   * Limpia todas las tareas completadas/fallidas
   */
  clearCompletedTasks() {
    const toRemove: string[] = [];
    this.tasks.forEach((task, id) => {
      if (task.status === 'completed' || task.status === 'failed') {
        toRemove.push(id);
      }
    });
    toRemove.forEach(id => this.tasks.delete(id));
    this.notifyListeners();
  }

  /**
   * Desconecta el WebSocket
   */
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}

// Singleton instance
export const BackgroundTaskManager = new BackgroundTaskManagerClass();

// Hook de React para usar el manager
export function useBackgroundTasks() {
  const [tasks, setTasks] = React.useState<BackgroundTask[]>([]);

  React.useEffect(() => {
    // Cargar tareas iniciales
    setTasks(BackgroundTaskManager.getAllTasks());

    // Suscribirse a cambios
    const unsubscribe = BackgroundTaskManager.subscribe(setTasks);

    // Solicitar permisos de notificación
    BackgroundTaskManager.requestNotificationPermission();

    // Cleanup
    return unsubscribe;
  }, []);

  return {
    tasks,
    activeTasks: tasks.filter(t => t.status === 'in_progress' || t.status === 'pending'),
    completedTasks: tasks.filter(t => t.status === 'completed'),
    failedTasks: tasks.filter(t => t.status === 'failed'),
    clearCompleted: () => BackgroundTaskManager.clearCompletedTasks(),
    getTask: (id: string) => BackgroundTaskManager.getTask(id)
  };
}

// Para uso fuera de React
import React from 'react';
export default BackgroundTaskManager;

