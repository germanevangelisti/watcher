import { useState, useEffect, useRef } from 'react';
import { 
  Paper, 
  Text, 
  Stack, 
  Group, 
  TextInput, 
  Button, 
  ScrollArea,
  Avatar,
  ActionIcon,
  Badge
} from '@mantine/core';
import { IconSend, IconRobot, IconUser, IconTrash } from '@tabler/icons-react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

interface AgentChatProps {
  height?: number;
}

export function AgentChat({ height = 500 }: AgentChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const viewport = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Scroll to bottom when new messages arrive
    if (viewport.current) {
      viewport.current.scrollTo({ 
        top: viewport.current.scrollHeight, 
        behavior: 'smooth' 
      });
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch('http://localhost:8001/api/v1/agents/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: input })
      });

      const data = await response.json();

      if (data.success) {
        const assistantMessage: Message = {
          role: 'assistant',
          content: data.response,
          timestamp: data.timestamp
        };
        setMessages(prev => [...prev, assistantMessage]);
      } else {
        const errorMessage: Message = {
          role: 'assistant',
          content: `Error: ${data.error}`,
          timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Error: Could not connect to agent',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleClearHistory = async () => {
    try {
      await fetch('http://localhost:8001/api/v1/agents/chat/clear', {
        method: 'POST'
      });
      setMessages([]);
    } catch (error) {
      console.error('Error clearing history:', error);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Paper p="md" withBorder style={{ height }}>
      <Stack gap="md" style={{ height: '100%' }}>
        <Group justify="space-between">
          <Group>
            <Avatar color="blue" radius="xl">
              <IconRobot size={20} />
            </Avatar>
            <div>
              <Text fw={600}>Insight Agent</Text>
              <Badge size="sm" color="green" variant="light">Online</Badge>
            </div>
          </Group>
          <ActionIcon 
            variant="subtle" 
            color="red"
            onClick={handleClearHistory}
            disabled={messages.length === 0}
          >
            <IconTrash size={18} />
          </ActionIcon>
        </Group>

        <ScrollArea 
          style={{ flex: 1 }}
          viewportRef={viewport}
        >
          <Stack gap="md" p="xs">
            {messages.length === 0 ? (
              <Text c="dimmed" ta="center" mt="xl">
                Start a conversation with the Insight Agent
              </Text>
            ) : (
              messages.map((message, index) => (
                <Group 
                  key={index} 
                  align="flex-start"
                  justify={message.role === 'user' ? 'flex-end' : 'flex-start'}
                >
                  {message.role === 'assistant' && (
                    <Avatar color="blue" radius="xl" size="sm">
                      <IconRobot size={16} />
                    </Avatar>
                  )}
                  
                  <Paper 
                    p="sm" 
                    withBorder
                    style={{ 
                      maxWidth: '70%',
                      background: message.role === 'user' ? '#228be6' : '#f8f9fa',
                      color: message.role === 'user' ? 'white' : 'black'
                    }}
                  >
                    <Text size="sm" style={{ whiteSpace: 'pre-wrap' }}>
                      {message.content}
                    </Text>
                    <Text 
                      size="xs" 
                      c={message.role === 'user' ? 'white' : 'dimmed'} 
                      mt="xs"
                      style={{ opacity: 0.7 }}
                    >
                      {new Date(message.timestamp).toLocaleTimeString()}
                    </Text>
                  </Paper>

                  {message.role === 'user' && (
                    <Avatar color="gray" radius="xl" size="sm">
                      <IconUser size={16} />
                    </Avatar>
                  )}
                </Group>
              ))
            )}
          </Stack>
        </ScrollArea>

        <Group gap="xs">
          <TextInput
            flex={1}
            placeholder="Ask a question about your data..."
            value={input}
            onChange={(e) => setInput(e.currentTarget.value)}
            onKeyPress={handleKeyPress}
            disabled={loading}
          />
          <Button 
            onClick={handleSend}
            loading={loading}
            leftSection={<IconSend size={16} />}
          >
            Send
          </Button>
        </Group>
      </Stack>
    </Paper>
  );
}





