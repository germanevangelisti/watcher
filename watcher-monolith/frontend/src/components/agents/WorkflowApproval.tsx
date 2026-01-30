import { useState } from 'react';
import { 
  Modal, 
  Paper, 
  Text, 
  Stack, 
  Group, 
  Button, 
  Badge,
  JsonInput,
  Textarea,
  Alert
} from '@mantine/core';
import { IconAlertCircle, IconCheck, IconX } from '@tabler/icons-react';

interface Task {
  task_id: string;
  task_type: string;
  agent: string;
  parameters: Record<string, any>;
  status: string;
  priority: number;
  requires_approval: boolean;
}

interface WorkflowApprovalProps {
  workflowId: string;
  workflowName: string;
  tasks: Task[];
  opened: boolean;
  onClose: () => void;
  onApprove: (taskId: string, modifications?: Record<string, any>) => Promise<void>;
  onReject: (taskId: string, reason?: string) => Promise<void>;
}

export function WorkflowApproval({
  workflowId,
  workflowName,
  tasks,
  opened,
  onClose,
  onApprove,
  onReject
}: WorkflowApprovalProps) {
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [modifications, setModifications] = useState<string>('{}');
  const [rejectReason, setRejectReason] = useState('');
  const [loading, setLoading] = useState(false);

  const awaitingTasks = tasks.filter(t => t.status === 'waiting_approval');

  const handleApprove = async () => {
    if (!selectedTask) return;
    
    setLoading(true);
    try {
      let mods = undefined;
      try {
        const parsed = JSON.parse(modifications);
        if (Object.keys(parsed).length > 0) {
          mods = parsed;
        }
      } catch (e) {
        // Ignore JSON parse errors for empty modifications
      }
      
      await onApprove(selectedTask.task_id, mods);
      setSelectedTask(null);
      setModifications('{}');
    } catch (error) {
      console.error('Error approving task:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async () => {
    if (!selectedTask) return;
    
    setLoading(true);
    try {
      await onReject(selectedTask.task_id, rejectReason || undefined);
      setSelectedTask(null);
      setRejectReason('');
    } catch (error) {
      console.error('Error rejecting task:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal 
      opened={opened} 
      onClose={onClose}
      size="xl"
      title={`Workflow Approval: ${workflowName}`}
    >
      <Stack gap="md">
        {awaitingTasks.length === 0 ? (
          <Alert icon={<IconCheck size={16} />} color="green">
            No tasks awaiting approval
          </Alert>
        ) : (
          <>
            <Alert icon={<IconAlertCircle size={16} />} color="yellow">
              {awaitingTasks.length} task(s) awaiting your approval
            </Alert>

            <Stack gap="sm">
              {awaitingTasks.map((task) => (
                <Paper 
                  key={task.task_id} 
                  p="md" 
                  withBorder
                  style={{ 
                    cursor: 'pointer',
                    border: selectedTask?.task_id === task.task_id ? '2px solid #228be6' : undefined
                  }}
                  onClick={() => setSelectedTask(task)}
                >
                  <Group justify="space-between" mb="xs">
                    <div>
                      <Text fw={600}>{task.task_type}</Text>
                      <Text size="sm" c="dimmed">Agent: {task.agent}</Text>
                    </div>
                    <Badge color="yellow">Awaiting Approval</Badge>
                  </Group>
                  
                  <Text size="sm" c="dimmed">Parameters:</Text>
                  <pre style={{ 
                    fontSize: '12px', 
                    background: '#f8f9fa', 
                    padding: '8px',
                    borderRadius: '4px',
                    overflow: 'auto'
                  }}>
                    {JSON.stringify(task.parameters, null, 2)}
                  </pre>
                </Paper>
              ))}
            </Stack>

            {selectedTask && (
              <Paper p="md" withBorder style={{ background: '#f8f9fa' }}>
                <Stack gap="md">
                  <Text fw={600} size="lg">Review Task: {selectedTask.task_type}</Text>
                  
                  <div>
                    <Text size="sm" fw={600} mb="xs">Modify Parameters (Optional)</Text>
                    <JsonInput
                      placeholder="Enter JSON modifications"
                      value={modifications}
                      onChange={setModifications}
                      minRows={4}
                      formatOnBlur
                      autosize
                    />
                    <Text size="xs" c="dimmed" mt="xs">
                      Only modified fields will be applied
                    </Text>
                  </div>

                  <div>
                    <Text size="sm" fw={600} mb="xs">Rejection Reason (if rejecting)</Text>
                    <Textarea
                      placeholder="Enter reason for rejection..."
                      value={rejectReason}
                      onChange={(e) => setRejectReason(e.currentTarget.value)}
                      minRows={2}
                    />
                  </div>

                  <Group justify="flex-end">
                    <Button 
                      color="red" 
                      leftSection={<IconX size={16} />}
                      onClick={handleReject}
                      loading={loading}
                      disabled={!rejectReason}
                    >
                      Reject Task
                    </Button>
                    <Button 
                      color="green" 
                      leftSection={<IconCheck size={16} />}
                      onClick={handleApprove}
                      loading={loading}
                    >
                      Approve Task
                    </Button>
                  </Group>
                </Stack>
              </Paper>
            )}
          </>
        )}
      </Stack>
    </Modal>
  );
}





