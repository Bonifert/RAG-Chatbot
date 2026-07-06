import { useState } from 'react'
import { toast } from "sonner"
import { Send } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Spinner } from "@/components/ui/spinner"
import {
  Message,
  MessageContent,
  MessageGroup,
} from "@/components/ui/message"
import {
  MessageScrollerProvider,
  MessageScroller,
  MessageScrollerViewport,
  MessageScrollerContent,
  MessageScrollerItem,
  MessageScrollerButton,
} from "@/components/ui/message-scroller"
import { EventSourceParserStream } from 'eventsource-parser/stream'

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  sources?: Sources;
}

type Sources = Record<string, string[]>

export function ChatSection() {
  const [userMessage, setUserMessage] = useState<string>("");
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  async function ask() {
    if (!userMessage.trim() || isLoading) return;
    setIsLoading(true);
    try {
      const url = "http://localhost:8000/ask/stream";
      const body = {
        question: userMessage,
        history: chatHistory.map(e => ({ role: e.role, content: e.content }))
      };
      const response = await fetch(url, {
        body: JSON.stringify(body),
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });
      if (response.ok) {
        setChatHistory(prev => [...prev,
        { role: "user", content: userMessage },
        { role: "assistant", content: "" }
        ]);
        setUserMessage("");
        const stream = response.body!
          .pipeThrough(new TextDecoderStream())
          .pipeThrough(new EventSourceParserStream());

        for await (const event of stream) {
          const data = JSON.parse(event.data);
          if (data.token) {
            setChatHistory(prev => {
              const updated = [...prev];
              updated[updated.length - 1].content += data.token;
              return updated;
            });
          } else if (data.sources) {
            setChatHistory(prev => {
              const updated = [...prev];
              updated[updated.length - 1].sources = data.sources;
              return updated;
            });
          }
        }
        return;
      }
      toast.error("Unexpected error occured. Please try again later.");
    } catch (error) {
      console.error(error);
      toast.error("Unexpected error occured. Please try again later.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <MessageScrollerProvider>
      <div className="flex flex-1 flex-col rounded-2xl border border-border bg-card shadow-sm overflow-hidden">
        <MessageScroller className="flex-1">
          <MessageScrollerViewport className="px-4 py-4">
            <MessageScrollerContent>
              {chatHistory.length === 0 && (
                <MessageScrollerItem scrollAnchor>
                  <p className="text-center text-sm text-muted-foreground">
                    Ask about the uploaded documents.
                  </p>
                </MessageScrollerItem>
              )}
              {chatHistory.map((msg, i) => (
                <MessageScrollerItem key={i} scrollAnchor={i === chatHistory.length - 1}>
                  <MessageGroup>
                    <Message align={msg.role === "user" ? "end" : "start"}>
                      <MessageContent>
                        <div className={
                          msg.role === "user"
                            ? "self-end rounded-2xl rounded-br-sm bg-primary px-4 py-2 text-primary-foreground"
                            : "rounded-2xl rounded-bl-sm bg-muted px-4 py-2 text-foreground"
                        }>
                          {msg.content || (msg.role === "assistant" && isLoading && (
                            <Spinner className="size-3.5" />
                          ))}
                        </div>
                        {msg.sources && Object.keys(msg.sources).length > 0 && (
                          <div className="mt-1 flex flex-wrap gap-1.5 px-1">
                            {Object.keys(msg.sources).map(source => (
                              <span key={source} className="rounded-full border px-2.5 py-0.5 text-xs text-muted-foreground">
                                {source}
                              </span>
                            ))}
                          </div>
                        )}
                      </MessageContent>
                    </Message>
                  </MessageGroup>
                </MessageScrollerItem>
              ))}
            </MessageScrollerContent>
          </MessageScrollerViewport>
          <MessageScrollerButton />
        </MessageScroller>

        <div className="flex gap-2 border-t border-border px-4 py-3">
          <Input
            value={userMessage}
            onChange={e => setUserMessage(e.target.value)}
            onKeyDown={e => e.key === "Enter" && ask()}
            placeholder="Write a question..."
            disabled={isLoading}
            className="h-10 rounded-xl"
          />
          <Button
            onClick={ask}
            disabled={isLoading || !userMessage.trim()}
            size="icon"
            className="size-10 shrink-0 rounded-xl"
          >
            {isLoading ? <Spinner /> : <Send className="size-4" />}
          </Button>
        </div>
      </div>
    </MessageScrollerProvider>
  )
}
