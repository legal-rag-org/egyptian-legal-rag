export interface Citation {
    source: string;
    page: number;
    url: string;
    label: string;
}

export interface ChatMessage {
    id: string;
    role: "user" | "assistant";
    content: string;
    citations?: Citation[];
}