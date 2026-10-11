
import { useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import {
  createUser,
  loginUser,
  sendMessage as sendMessageApi,
  getConversations,
  getConversationMessages,
  type Conversation,
} from "./services/api.ts";

import "./App.css";

interface Citation {
  source: string;
  page: number;
  url: string;
  label: string;
}

interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  imageName?: string;
}

const suggestedQuestions = [
  "ما هي شروط استحقاق معاش التأمينات؟",
  "ما هي حقوق العامل عند إنهاء عقد العمل؟",
  "ما هي إجراءات التصالح في مخالفات البناء؟",
];

const MAX_IMAGE_SIZE = 10 * 1024 * 1024;

function App() {
  // Authentication
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userUuid, setUserUuid] = useState<string | null>(null);
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [registerLoading, setRegisterLoading] = useState(false);
  const [registerError, setRegisterError] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState("");

  // Chat
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const [conversationUuid, setConversationUuid] = useState<
    string | undefined
  >();

  const [activeConversationUuid, setActiveConversationUuid] = useState<
    string | null
  >(null);

  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imageError, setImageError] = useState("");

  // Sidebar
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [loadingConversations, setLoadingConversations] = useState(false);
  const [openingConversation, setOpeningConversation] = useState(false);
  const [conversationError, setConversationError] = useState("");

  // About
  const [showAbout, setShowAbout] = useState(false);

  // Load conversations
  const loadConversations = useCallback(async () => {
    if (!userUuid) return;

    setLoadingConversations(true);
    setConversationError("");

    try {
      const data = await getConversations(userUuid);
      setConversations(data);
    } catch (error) {
      console.error("Failed to load conversations:", error);
      setConversationError("تعذر تحميل المحادثات.");
    } finally {
      setLoadingConversations(false);
    }
  }, [userUuid]);

  useEffect(() => {
    if (isLoggedIn && userUuid) {
      void loadConversations();
    } else {
      setConversations([]);
    }
  }, [isLoggedIn, userUuid, loadConversations]);

  // Register
  const handleRegister = async () => {
    setRegisterError("");

    if (!username.trim() || !email.trim() || !password) {
      setRegisterError("من فضلك أدخل جميع البيانات.");
      return;
    }

    setRegisterLoading(true);

    try {
      await createUser(username.trim(), email.trim(), password);
      setAuthMode("login");
      setPassword("");
      setLoginError("");
    } catch (error) {
      console.error(error);
      setRegisterError(
        "فشل إنشاء الحساب. قد يكون البريد الإلكتروني أو اسم المستخدم مستخدمًا بالفعل.",
      );
    } finally {
      setRegisterLoading(false);
    }
  };

  // Login
  const handleLogin = async () => {
    setLoginError("");

    if (!email.trim() || !password) {
      setLoginError("من فضلك أدخل البريد الإلكتروني وكلمة المرور.");
      return;
    }

    setLoginLoading(true);

    try {
      const user = await loginUser(email.trim(), password);

      setUserUuid(user.user_uuid);
      setUsername(user.username);
      setEmail(user.email);
      setIsLoggedIn(true);

      setMessages([]);
      setConversationUuid(undefined);
      setActiveConversationUuid(null);
      setInput("");
      setSelectedImage(null);
      setImageError("");
    } catch (error) {
      console.error(error);
      setLoginError("البريد الإلكتروني أو كلمة المرور غير صحيحة.");
    } finally {
      setLoginLoading(false);
    }
  };

  // New conversation
  const handleNewConversation = () => {
    if (loading || openingConversation) return;

    setMessages([]);
    setInput("");
    setConversationUuid(undefined);
    setActiveConversationUuid(null);
    setSelectedImage(null);
    setImageError("");
    setConversationError("");
  };

  // Open existing conversation
  const handleOpenConversation = async (conversation: Conversation) => {
    if (
      !userUuid ||
      loading ||
      openingConversation ||
      conversation.conversation_uuid === activeConversationUuid
    ) {
      return;
    }

    setOpeningConversation(true);
    setConversationError("");

    try {
      const data = await getConversationMessages(
        userUuid,
        conversation.conversation_uuid,
      );

      const loadedMessages: Message[] = data.messages.map(
        (message, index) => ({
          id: Date.now() + index,
          role:
            String(message.role).toLowerCase() === "user"
              ? "user"
              : "assistant",
          content: message.content,
          citations: [],
        }),
      );

      setMessages(loadedMessages);
      setConversationUuid(data.conversation_uuid);
      setActiveConversationUuid(data.conversation_uuid);
      setInput("");
      setSelectedImage(null);
      setImageError("");
    } catch (error) {
      console.error("Failed to open conversation:", error);
      setConversationError("تعذر فتح المحادثة. حاول مرة أخرى.");
    } finally {
      setOpeningConversation(false);
    }
  };

  // Image selection
  const handleImageChange = (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const file = event.target.files?.[0];

    event.target.value = "";

    if (!file) return;

    setImageError("");

    if (!file.type.startsWith("image/")) {
      setImageError("من فضلك اختر ملف صورة صالحًا.");
      return;
    }

    if (file.size > MAX_IMAGE_SIZE) {
      setImageError("حجم الصورة يجب ألا يتجاوز 10 ميجابايت.");
      return;
    }

    setSelectedImage(file);
  };

  // Send message
  const sendMessage = async (questionOverride?: string) => {
    const question = (questionOverride ?? input).trim();
    const imageToSend = selectedImage;

    if (
      (!question && !imageToSend) ||
      loading ||
      openingConversation ||
      !userUuid
    ) {
      return;
    }

    const isFirstMessage = !conversationUuid;

    const userMessage: Message = {
      id: Date.now(),
      role: "user",
      content: question || "ما محتوى هذه الصورة؟",
      imageName: imageToSend?.name,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setImageError("");
    setLoading(true);

    try {
      const response = await sendMessageApi(
        question,
        userUuid,
        conversationUuid,
        imageToSend,
      );

      if (response.conversation_uuid) {
        setConversationUuid(response.conversation_uuid);
        setActiveConversationUuid(response.conversation_uuid);
      }

      const assistantMessage: Message = {
        id: Date.now() + 1,
        role: "assistant",
        content: response.answer,
        citations: response.citations ?? [],
      };

      setMessages((prev) => [...prev, assistantMessage]);

      if (imageToSend === selectedImage) {
        setSelectedImage(null);
      }

      if (isFirstMessage) {
        await loadConversations();
      }
    } catch (error) {
      console.error(error);

      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: "assistant",
          content: "حصل خطأ ما. من فضلك حاول مرة أخرى.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Suggested questions
  const handleSuggestedQuestion = (question: string) => {
    setInput(question);
  };

  // Enter key
  const handleKeyDown = (
    event: React.KeyboardEvent<HTMLTextAreaElement>,
  ) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void sendMessage();
    }
  };

  // Login page
  if (!isLoggedIn && authMode === "login") {
    return (
      <div className="auth-container" dir="rtl">
        <div className="auth-card">
          <h1>Legal RAG</h1>
          <p className="auth-subtitle">تسجيل الدخول إلى حسابك</p>

          <div className="form-group">
            <label>البريد الإلكتروني</label>
            <input
              type="email"
              placeholder="أدخل بريدك الإلكتروني"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>

          <div className="form-group">
            <label>كلمة المرور</label>
            <input
              type="password"
              placeholder="أدخل كلمة المرور"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") void handleLogin();
              }}
            />
          </div>

          {loginError && <div className="error-message">{loginError}</div>}

          <button
            className="auth-button"
            onClick={handleLogin}
            disabled={loginLoading}
          >
            {loginLoading ? "جاري تسجيل الدخول..." : "تسجيل الدخول"}
          </button>

          <div className="auth-switch">
            <span>ليس لديك حساب؟</span>
            <button
              onClick={() => {
                setAuthMode("register");
                setLoginError("");
              }}
            >
              إنشاء حساب
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Register page
  if (!isLoggedIn && authMode === "register") {
    return (
      <div className="auth-container" dir="rtl">
        <div className="auth-card">
          <h1>Legal RAG</h1>
          <p className="auth-subtitle">إنشاء حسابك</p>

          <div className="form-group">
            <label>اسم المستخدم</label>
            <input
              type="text"
              placeholder="أدخل اسم المستخدم"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
            />
          </div>

          <div className="form-group">
            <label>البريد الإلكتروني</label>
            <input
              type="email"
              placeholder="أدخل بريدك الإلكتروني"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>

          <div className="form-group">
            <label>كلمة المرور</label>
            <input
              type="password"
              placeholder="أدخل كلمة المرور"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>

          {registerError && (
            <div className="error-message">{registerError}</div>
          )}

          <button
            className="auth-button"
            onClick={handleRegister}
            disabled={registerLoading}
          >
            {registerLoading ? "جاري إنشاء الحساب..." : "إنشاء الحساب"}
          </button>

          <div className="auth-switch">
            <span>لديك حساب بالفعل؟</span>
            <button
              onClick={() => {
                setAuthMode("login");
                setRegisterError("");
              }}
            >
              تسجيل الدخول
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Main application
  return (
    <div className="app" dir="rtl">
      <header className="header">
        <div className="header-info">
          <h1>المساعد القانوني المصري</h1>
          <p>أهلًا بك، {username}</p>
        </div>

        <div className="header-actions">
          <button
            className="sidebar-toggle-button"
            onClick={() => setSidebarOpen((open) => !open)}
            aria-label={sidebarOpen ? "إخفاء المحادثات" : "عرض المحادثات"}
            title={sidebarOpen ? "إخفاء المحادثات" : "عرض المحادثات"}
          >
            ☰
          </button>

          <button
            className="new-conversation-button"
            onClick={handleNewConversation}
            disabled={loading || openingConversation}
            title="بدء محادثة جديدة"
          >
            <span aria-hidden="true">+</span>
            <span>محادثة جديدة</span>
          </button>

          <button
            className="about-button"
            onClick={() => setShowAbout(true)}
            aria-label="عن التطبيق"
          >
            عن التطبيق
          </button>
        </div>
      </header>

      {showAbout && (
        <div
          className="about-overlay"
          onClick={() => setShowAbout(false)}
        >
          <div
            className="about-modal"
            dir="rtl"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              className="about-close"
              onClick={() => setShowAbout(false)}
              aria-label="إغلاق"
            >
              ×
            </button>

            <div className="about-icon" aria-hidden="true">
              ⚖
            </div>

            <h2>عن المساعد القانوني المصري</h2>

            <p className="about-description">
              مساعد قانوني ذكي يعتمد على تقنية RAG للوصول إلى المعلومات
              القانونية من مصادر موثوقة، ومساعدتك في فهم القوانين واللوائح
              المصرية والإجابة عن استفساراتك مع إظهار المصادر ذات الصلة.
            </p>

            <h3>المجالات المتاحة</h3>

            <div className="legal-domains">
              <span>التأمينات الاجتماعية والمعاشات</span>
              <span>قانون العمل</span>
              <span>القانون الضريبي</span>
              <span>قانون الشركات</span>
              <span>قانون الخدمة المدنية</span>
              <span>قانون الجمارك</span>
              <span>التصالح في مخالفات البناء</span>
            </div>

            <div className="about-note">
              <strong>تنبيه:</strong>
              <span>
                المعلومات المقدمة للتوعية والاسترشاد ولا تُعد بديلًا عن
                الاستشارة القانونية المتخصصة.
              </span>
            </div>
          </div>
        </div>
      )}

      <div className="app-layout">
        {sidebarOpen && (
          <aside className="conversation-sidebar">
            <button
              className="sidebar-new-chat"
              onClick={handleNewConversation}
              disabled={loading || openingConversation}
            >
              <span aria-hidden="true">+</span>
              محادثة جديدة
            </button>

            <h2 className="sidebar-heading">المحادثات</h2>

            {conversationError && (
              <p className="sidebar-error">{conversationError}</p>
            )}

            {loadingConversations ? (
              <p className="sidebar-status">جاري تحميل المحادثات...</p>
            ) : conversations.length === 0 ? (
              <p className="sidebar-status">
                لا توجد محادثات محفوظة حتى الآن.
              </p>
            ) : (
              <div className="conversation-list">
                {conversations.map((conversation) => (
                  <button
                    key={conversation.conversation_uuid}
                    className={`conversation-item ${activeConversationUuid === conversation.conversation_uuid
                        ? "active"
                        : ""
                      }`}
                    onClick={() => void handleOpenConversation(conversation)}
                    disabled={loading || openingConversation}
                    title={conversation.title}
                  >
                    <span className="conversation-item-icon" aria-hidden="true">
                      ▤
                    </span>
                    <span className="conversation-item-title">
                      {conversation.title || "محادثة جديدة"}
                    </span>
                  </button>
                ))}
              </div>
            )}

            {openingConversation && (
              <p className="sidebar-status">جاري فتح المحادثة...</p>
            )}
          </aside>
        )}

        <main className="chat-container">
          <div className="messages">
            {messages.length === 0 && (
              <div className="empty-state">
                <h2>إزاي أقدر أساعدك؟</h2>
                <p>اسألني عن القوانين واللوائح المصرية.</p>

                <div className="suggested-questions">
                  <div className="suggested-title">أمثلة على الأسئلة</div>

                  {suggestedQuestions.map((question) => (
                    <button
                      key={question}
                      className="suggested-question"
                      onClick={() => handleSuggestedQuestion(question)}
                    >
                      <span>{question}</span>
                      <span className="suggested-arrow" aria-hidden="true">
                        ←
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((message) => (
              <div
                key={message.id}
                className={`message ${message.role}`}
              >
                <div className="message-content">
                  {message.imageName && (
                    <div className="message-image-attachment">
                      <span aria-hidden="true">🖼️</span>
                      <span>{message.imageName}</span>
                    </div>
                  )}

                  {message.role === "assistant" ? (
                    <div className="markdown-content" dir="rtl">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          a: ({ children, href }) => (
                            <a
                              href={href}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              {children}
                            </a>
                          ),
                        }}
                      >
                        {message.content}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    message.content
                  )}
                </div>

                {/* Expandable citation panel beside the answer */}
                {message.role === "assistant" &&
                  message.citations &&
                  message.citations.length > 0 && (
                    <aside className="citations">
                      <div className="citations-title">
                        المصادر ({message.citations.length})
                      </div>

                      {message.citations.map((citation, index) => (
                        <details
                          className="citation-details"
                          key={`${citation.url}-${citation.source}-${index}`}
                        >
                          <summary className="citation-summary">
                            <span className="citation-label">
                              {citation.label ||
                                citation.source ||
                                `المصدر ${index + 1}`}
                            </span>

                            {citation.page != null && (
                              <span className="citation-page">
                                صـ {citation.page}
                              </span>
                            )}
                          </summary>

                          <div className="citation-content">
                            <div className="citation-source-name">
                              <strong>المصدر: </strong>
                              {citation.source || "غير محدد"}
                            </div>

                            {citation.page != null && (
                              <div>
                                <strong>الصفحة: </strong>
                                {citation.page}
                              </div>
                            )}

                            {citation.url && (
                              <a
                                href={citation.url}
                                target="_blank"
                                rel="noopener noreferrer"
                              >
                                فتح المستند الأصلي ↗
                              </a>
                            )}
                          </div>
                        </details>
                      ))}
                    </aside>
                  )}
              </div>
            ))}

            {loading && (
              <div className="message assistant">
                <div className="message-content">
                  جاري التفكير...
                </div>
              </div>
            )}
          </div>

          {/* Fixed, narrower input */}
          <div className="input-container">
            <div className="chat-input-area">
              <div className="image-upload">
                <label
                  htmlFor="chat-image"
                  className="image-upload-button"
                >
                  <span aria-hidden="true">📎</span>
                  <span>إرفاق صورة</span>
                </label>

                <input
                  id="chat-image"
                  type="file"
                  accept="image/*"
                  hidden
                  disabled={loading || openingConversation}
                  onChange={handleImageChange}
                />

                {selectedImage && (
                  <div className="selected-image">
                    <span aria-hidden="true">🖼️</span>
                    <span className="selected-image-name">
                      {selectedImage.name}
                    </span>
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedImage(null);
                        setImageError("");
                      }}
                      disabled={loading}
                      aria-label="إزالة الصورة"
                      title="إزالة الصورة"
                    >
                      ×
                    </button>
                  </div>
                )}
              </div>

              {imageError && (
                <div className="error-message image-error">
                  {imageError}
                </div>
              )}

              <textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="اكتب سؤالك القانوني هنا..."
                rows={1}
                disabled={loading || openingConversation}
                dir="rtl"
              />

              <button
                onClick={() => void sendMessage()}
                disabled={
                  loading ||
                  openingConversation ||
                  (!input.trim() && !selectedImage) ||
                  !userUuid
                }
                aria-label="إرسال السؤال"
                title="إرسال السؤال"
              >
                {loading ? "..." : "إرسال"}
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
