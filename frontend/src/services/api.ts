const API_URL = "http://localhost:8000";

export interface Citation {
    source: string;
    page: number;
    url: string;
    label: string;
}

export interface ChatResponse {
    signal: string;
    conversation_uuid: string;
    title?: string;
    answer: string;
    citations: Citation[];
}

export interface UserResponse {
    user_uuid: string;
    username: string;
    email: string;
}


export async function sendMessage(
    question: string,
    userUuid: string,
    conversationUuid?: string,
    image?: File | null,
): Promise<ChatResponse> {
    const formData = new FormData();

    formData.append("text", question);
    formData.append("user_uuid", userUuid);

    if (conversationUuid) {
        formData.append("conversation_uuid", conversationUuid);
    }

    if (image) {
        formData.append("image", image);
    }

    const response = await fetch(
        `${API_URL}/api/v1/nlp/chat/1`,
        {
            method: "POST",
            body: formData,
        },
    );

    if (!response.ok) {
        const errorText = await response.text();
        console.error("Backend error:", errorText);
        throw new Error(`Request failed: ${response.status}`);
    }

    return response.json();
}


export async function createUser(
    username: string,
    email: string,
    password: string,
): Promise<UserResponse> {
    const response = await fetch(
        `${API_URL}/api/v1/users`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                username,
                email,
                password,
            }),
        },
    );

    if (!response.ok) {
        const errorText = await response.text();

        console.error("Backend status:", response.status);
        console.error("Backend error:", errorText);

        throw new Error(errorText);
    }

    return response.json();
}

export async function loginUser(
    email: string,
    password: string,
): Promise<UserResponse> {
    const response = await fetch(
        `${API_URL}/api/v1/users/login`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                email,
                password,
            }),
        },
    );

    if (!response.ok) {
        const errorText = await response.text();

        console.error("Backend status:", response.status);
        console.error("Backend error:", errorText);

        throw new Error(errorText);
    }

    return response.json();
}

export interface Conversation {
    conversation_uuid: string;
    title: string;
    summary: string | null;
    created_at: string;
    updated_at: string | null;
}

export interface ConversationMessagesResponse {
    conversation_uuid: string;
    title: string;
    messages: {
        role: "user" | "assistant";
        content: string;
    }[];
}

export async function getConversations(
    userUuid: string,
): Promise<Conversation[]> {
    const response = await fetch(
        `${API_URL}/api/v1/nlp/conversations/1?user_uuid=${encodeURIComponent(userUuid)}`,
    );

    if (!response.ok) {
        throw new Error("Failed to load conversations");
    }

    const data = await response.json();
    return data.conversations;
}

export async function getConversationMessages(
    userUuid: string,
    conversationUuid: string,
): Promise<ConversationMessagesResponse> {
    const response = await fetch(
        `${API_URL}/api/v1/nlp/conversations/1/${encodeURIComponent(conversationUuid)}/messages?user_uuid=${encodeURIComponent(userUuid)}`,
    );

    if (!response.ok) {
        throw new Error("Failed to load conversation messages");
    }

    return response.json();
}