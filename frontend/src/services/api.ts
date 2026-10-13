const API_URL = "http://localhost:8000";

// Types 

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

export interface LoginResponse {
    access_token: string;
    token_type: string;
    user: UserResponse;
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

// Authentication 

function getAuthHeaders(): HeadersInit {
    const accessToken = localStorage.getItem("access_token");

    if (!accessToken) {
        throw new Error("You must log in first.");
    }

    return {
        Authorization: `Bearer ${accessToken}`,
    };
}

export async function createUser(
    username: string,
    email: string,
    password: string,
): Promise<UserResponse> {
    const response = await fetch(`${API_URL}/api/v1/users`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            username,
            email,
            password,
        }),
    });

    if (!response.ok) {
        const errorText = await response.text();
        console.error("Registration error:", errorText);
        throw new Error(errorText);
    }

    return response.json();
}

export async function loginUser(
    email: string,
    password: string,
): Promise<LoginResponse> {
    const response = await fetch(`${API_URL}/api/v1/users/login`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            email,
            password,
        }),
    });

    if (!response.ok) {
        const errorText = await response.text();
        console.error("Login error:", errorText);
        throw new Error(errorText);
    }

    const data: LoginResponse = await response.json();

    // Save the token for subsequent authenticated requests.
    localStorage.setItem("access_token", data.access_token);

    return data;
}

export function logoutUser(): void {
    localStorage.removeItem("access_token");
}

// Chat 

export async function sendMessage(
    question: string,
    conversationUuid?: string,
    image?: File | null,
): Promise<ChatResponse> {
    const formData = new FormData();

    formData.append("text", question);

    if (conversationUuid) {
        formData.append("conversation_uuid", conversationUuid);
    }

    if (image) {
        formData.append("image", image);
    }

    const response = await fetch(`${API_URL}/api/v1/nlp/chat/1`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: formData,
    });

    if (!response.ok) {
        const errorText = await response.text();
        console.error("Chat error:", errorText);
        throw new Error(`Request failed: ${response.status} - ${errorText}`);
    }

    return response.json();
}

// Conversations

export async function getConversations(): Promise<Conversation[]> {
    const response = await fetch(
        `${API_URL}/api/v1/nlp/conversations/1`,
        {
            headers: getAuthHeaders(),
        },
    );

    if (!response.ok) {
        const errorText = await response.text();
        console.error("Get conversations error:", errorText);
        throw new Error("Failed to load conversations");
    }

    const data = await response.json();
    return data.conversations;
}

export async function getConversationMessages(
    conversationUuid: string,
): Promise<ConversationMessagesResponse> {
    const response = await fetch(
        `${API_URL}/api/v1/nlp/conversations/1/${encodeURIComponent(conversationUuid)}/messages`,
        {
            headers: getAuthHeaders(),
        },
    );

    if (!response.ok) {
        const errorText = await response.text();
        console.error("Get conversation messages error:", errorText);
        throw new Error("Failed to load conversation messages");
    }

    return response.json();
}