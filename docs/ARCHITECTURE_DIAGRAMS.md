# Application Architecture Diagrams

**Version:** 1.0  
**Date:** December 22, 2025  
**Project:** WhatsApp Clone with E2E Encryption  

---

## 1. High-Level System Architecture

```mermaid
flowchart TB
    subgraph Clients["Client Layer"]
        WEB["🌐 Web Browser<br/>(React 18)"]
        CLI["🐍 Python CLI<br/>(whatsapp_cli.py)"]
        SDK["📦 Python SDK<br/>(WhatsAppClient)"]
    end

    subgraph Edge["Cloudflare Edge Network"]
        WORKER["⚡ Cloudflare Worker<br/>(index.ts)"]
        DO["🔄 Durable Object<br/>(ChatRoom.ts)"]
    end

    subgraph Storage["Data Layer"]
        D1[("💾 Cloudflare D1<br/>(SQLite)")]
    end

    WEB <-->|"HTTPS/WSS"| WORKER
    CLI <-->|"HTTPS/WSS"| WORKER
    SDK <-->|"HTTPS/WSS"| WORKER
    
    WORKER <-->|"RPC"| DO
    WORKER <-->|"SQL"| D1
    DO <-->|"SQL"| D1
```

---

## 2. Component Architecture

```mermaid
flowchart LR
    subgraph Backend["Backend (Cloudflare Workers)"]
        direction TB
        API["REST API<br/>(/api/*)"]
        AUTH["Auth Manager<br/>(JWT/bcrypt)"]
        KEYS["Key Manager<br/>(Prekeys)"]
        MSG["Message Handler"]
        GRP["Group Handler"]
        ADMIN["Admin Handler"]
        
        API --> AUTH
        API --> KEYS
        API --> MSG
        API --> GRP
        API --> ADMIN
    end

    subgraph DurableObject["Durable Object (ChatRoom)"]
        direction TB
        WS["WebSocket Manager"]
        PRESENCE["Presence Manager"]
        TYPING["Typing Handler"]
        BROADCAST["Broadcast Engine"]
        
        WS --> PRESENCE
        WS --> TYPING
        WS --> BROADCAST
    end

    subgraph Frontend["Frontend (React)"]
        direction TB
        APP["App.tsx"]
        LOGIN["Login/Register"]
        CHAT["ChatWindow"]
        USERS["UserList"]
        GROUPS["GroupList"]
        
        APP --> LOGIN
        APP --> CHAT
        APP --> USERS
        APP --> GROUPS
    end

    subgraph PythonClient["Python Client"]
        direction TB
        CLIENT["WhatsAppClient"]
        AUTHM["AuthManager"]
        CRYPTO["CryptoManager"]
        TRANS["Transport Layer"]
        STORE["Storage Layer"]
        
        CLIENT --> AUTHM
        CLIENT --> CRYPTO
        CLIENT --> TRANS
        CLIENT --> STORE
    end

    Frontend <-->|"HTTP/WS"| Backend
    PythonClient <-->|"HTTP/WS"| Backend
    Backend <--> DurableObject
```

---

## 3. End-to-End Encryption Flow

```mermaid
sequenceDiagram
    participant A as Alice (Sender)
    participant S as Server
    participant B as Bob (Recipient)

    Note over A,B: Key Registration Phase
    A->>A: Generate Identity Key (Curve25519)
    A->>A: Generate Signing Key (Ed25519)
    A->>A: Generate Signed Prekey
    A->>A: Generate 100 One-Time Prekeys
    A->>S: Upload Public Keys
    
    B->>B: Generate Keys
    B->>S: Upload Public Keys

    Note over A,B: Session Establishment (X3DH)
    A->>S: Request Bob's Prekey Bundle
    S->>A: Identity Key, Signed Prekey, One-Time Prekey
    
    A->>A: X3DH Key Agreement
    Note right of A: DH1: DH(IKa, SPKb)<br/>DH2: DH(EKa, IKb)<br/>DH3: DH(EKa, SPKb)<br/>DH4: DH(EKa, OPKb)
    A->>A: Derive Shared Secret (32 bytes)
    A->>A: Initialize Double Ratchet

    Note over A,B: Message Exchange
    A->>A: Encrypt with AES-256-GCM
    A->>S: Send Encrypted Message + X3DH Header
    S->>B: Forward Encrypted Message
    
    B->>B: Perform X3DH (derive same secret)
    B->>B: Initialize Double Ratchet
    B->>B: Decrypt Message
    
    Note over A,B: Subsequent Messages (Ratchet)
    A->>A: Symmetric Ratchet Step
    A->>S: Encrypted Message
    S->>B: Forward
    B->>B: Symmetric Ratchet + Decrypt
    
    B->>B: DH Ratchet (new keys)
    B->>S: Reply (new ratchet key in header)
    S->>A: Forward
    A->>A: DH Ratchet + Decrypt
```

---

## 4. Authentication Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant W as Worker
    participant D as D1 Database

    Note over C,D: Registration
    C->>W: POST /api/auth/register<br/>{username, password}
    W->>W: Validate (3-100 chars, 6+ chars)
    W->>W: Hash Password (bcrypt, factor 10)
    W->>W: Generate UUID v4
    W->>D: INSERT INTO users
    W->>W: Generate JWT (24h expiry)
    W->>C: {id, username, token}
    
    C->>C: Generate Crypto Keys
    C->>W: POST /api/users/prekeys<br/>{identityKey, signedPrekey, oneTimePrekeys}
    W->>D: INSERT INTO user_identity_keys, user_prekeys
    W->>C: {success: true}

    Note over C,D: Login
    C->>W: POST /api/auth/login<br/>{username, password}
    W->>D: SELECT * FROM users WHERE username = ?
    W->>W: Verify bcrypt hash
    W->>W: Generate JWT (24h expiry)
    W->>C: {id, username, token}

    Note over C,D: Authenticated Request
    C->>W: GET /api/messages<br/>Authorization: Bearer <token>
    W->>W: Verify JWT
    W->>D: SELECT * FROM messages
    W->>C: [messages]
```

---

## 5. Real-Time Messaging Flow

```mermaid
sequenceDiagram
    participant A as Alice
    participant DO as Durable Object
    participant B as Bob

    Note over A,DO,B: WebSocket Connection
    A->>DO: WebSocket Connect
    DO->>DO: Add to sessions map
    DO->>A: Online users list
    DO-->>B: Broadcast: Alice online

    B->>DO: WebSocket Connect
    DO->>DO: Add to sessions map
    DO-->>A: Broadcast: Bob online

    Note over A,DO,B: Send Message
    A->>A: Encrypt message (E2EE)
    A->>DO: {type: "message", to: Bob, content: encrypted}
    DO->>DO: Find Bob's session
    DO->>B: {type: "message", from: Alice, content: encrypted}
    B->>B: Decrypt message
    
    Note over A,DO,B: Message Status
    B->>DO: {type: "status", messageId, status: "delivered"}
    DO->>A: {type: "status", messageId, status: "delivered"}
    
    B->>DO: {type: "status", messageId, status: "read"}
    DO->>A: {type: "status", messageId, status: "read"}

    Note over A,DO,B: Typing Indicator
    A->>DO: {type: "typing", to: Bob, typing: true}
    DO->>B: {type: "typing", from: Alice, typing: true}
    Note right of B: Display "Alice is typing..."
    
    A->>DO: {type: "typing", to: Bob, typing: false}
    DO->>B: {type: "typing", from: Alice, typing: false}
    Note right of B: Hide typing indicator

    Note over A,DO,B: Disconnect
    A->>DO: WebSocket Close
    DO->>DO: Remove from sessions
    DO-->>B: Broadcast: Alice offline
```

---

## 6. Database Schema Diagram

```mermaid
erDiagram
    users {
        TEXT id PK "UUID v4"
        TEXT username UK "3-100 chars"
        TEXT password_hash "bcrypt"
        TEXT avatar
        TEXT role "user/admin"
        INTEGER is_active
        INTEGER lastSeen
        INTEGER created_at
    }

    user_identity_keys {
        TEXT id PK
        TEXT user_id FK
        TEXT identity_key "Curve25519 public"
        TEXT signing_key "Ed25519 public"
        TEXT fingerprint "SHA-256"
        INTEGER created_at
    }

    user_prekeys {
        TEXT id PK
        TEXT user_id FK
        INTEGER key_id
        TEXT prekey_type "signed/onetime"
        TEXT public_key
        TEXT signature
        INTEGER is_used
        INTEGER used_at
        INTEGER created_at
    }

    messages {
        TEXT id PK "UUID"
        TEXT fromUser FK
        TEXT toUser FK
        TEXT content "Encrypted"
        INTEGER timestamp
        TEXT status "sent/delivered/read"
    }

    groups {
        TEXT id PK "UUID"
        TEXT name
        TEXT description
        TEXT avatar
        TEXT created_by FK
        INTEGER created_at
    }

    group_members {
        TEXT id PK
        TEXT group_id FK
        TEXT user_id FK
        TEXT role "admin/member"
        INTEGER joined_at
    }

    group_messages {
        TEXT id PK "UUID"
        TEXT group_id FK
        TEXT from_user FK
        TEXT content "Encrypted"
        INTEGER timestamp
    }

    users ||--|| user_identity_keys : "has"
    users ||--o{ user_prekeys : "has many"
    users ||--o{ messages : "sends"
    users ||--o{ messages : "receives"
    users ||--o{ groups : "creates"
    users ||--o{ group_members : "joins"
    groups ||--o{ group_members : "has"
    groups ||--o{ group_messages : "contains"
    users ||--o{ group_messages : "sends"
```

---

## 7. Cryptographic Architecture

```mermaid
flowchart TB
    subgraph KeyGeneration["Key Generation (Registration)"]
        IK["Identity Key<br/>(Curve25519)"]
        SK["Signing Key<br/>(Ed25519)"]
        SPK["Signed Prekey<br/>(Curve25519 + Signature)"]
        OPK["One-Time Prekeys<br/>(100 × Curve25519)"]
    end

    subgraph X3DH["X3DH Key Agreement"]
        DH1["DH1: DH(IKa, SPKb)"]
        DH2["DH2: DH(EKa, IKb)"]
        DH3["DH3: DH(EKa, SPKb)"]
        DH4["DH4: DH(EKa, OPKb)"]
        SS["Shared Secret<br/>(32 bytes via HKDF)"]
        
        DH1 --> SS
        DH2 --> SS
        DH3 --> SS
        DH4 --> SS
    end

    subgraph DoubleRatchet["Double Ratchet"]
        RK["Root Key"]
        SCK["Sending Chain Key"]
        RCK["Receiving Chain Key"]
        MK["Message Key"]
        
        SS --> RK
        RK --> SCK
        RK --> RCK
        SCK --> MK
        RCK --> MK
    end

    subgraph Encryption["Message Encryption"]
        PT["Plaintext"]
        CT["Ciphertext"]
        AES["AES-256-GCM"]
        HDR["Ratchet Header"]
        
        PT --> AES
        MK --> AES
        AES --> CT
        CT --> HDR
    end

    IK --> X3DH
    SPK --> X3DH
    OPK --> X3DH
```

---

## 8. Python Client Architecture

```mermaid
flowchart TB
    subgraph WhatsAppClient["WhatsAppClient (client.py)"]
        direction LR
        REG["register()"]
        LOG["login()"]
        SEND["send_message()"]
        RECV["receive_message()"]
        GRP["send_group_message()"]
    end

    subgraph Auth["Auth Module"]
        AM["AuthManager"]
        VAL["Validation<br/>(Pydantic)"]
    end

    subgraph Crypto["Crypto Module"]
        direction TB
        KM["KeyManager<br/>(keys.py)"]
        X3["X3DH<br/>(x3dh.py)"]
        DR["DoubleRatchet<br/>(double_ratchet.py)"]
        FP["Fingerprint<br/>(keys.py)"]
    end

    subgraph Transport["Transport Module"]
        REST["RestClient<br/>(rest.py)"]
        WS["WebSocketClient<br/>(websocket.py)"]
    end

    subgraph Storage["Storage Module"]
        KS["KeyStorage"]
        SS["SessionStorage"]
        FS["FingerprintStorage"]
    end

    WhatsAppClient --> Auth
    WhatsAppClient --> Crypto
    WhatsAppClient --> Transport
    WhatsAppClient --> Storage

    AM --> VAL
    KM --> X3
    X3 --> DR
    REST --> WS
```

---

## 9. File Structure Diagram

```mermaid
flowchart TB
    subgraph Root["📁 whatsapp-clone/"]
        direction TB
        
        subgraph Src["📁 src/"]
            subgraph Worker["📁 worker/"]
                IDX["📄 index.ts<br/>(REST API)"]
                CR["📄 ChatRoom.ts<br/>(Durable Object)"]
                TYP["📄 types.ts"]
            end
            
            subgraph Client["📁 client/"]
                APP["📄 App.tsx"]
                MAIN["📄 main.tsx"]
                subgraph Comp["📁 components/"]
                    UL["📄 UserList.tsx"]
                    CW["📄 ChatWindow.tsx"]
                    GL["📄 GroupList.tsx"]
                end
            end
        end
        
        subgraph Python["📁 python-client/"]
            subgraph PySrc["📁 src/whatsapp_client/"]
                PCLI["📄 client.py"]
                PMOD["📄 models.py"]
                subgraph PyAuth["📁 auth/"]
                    PAM["📄 manager.py"]
                end
                subgraph PyCrypto["📁 crypto/"]
                    PKEY["📄 keys.py"]
                    PX3["📄 x3dh.py"]
                    PDR["📄 double_ratchet.py"]
                end
                subgraph PyTrans["📁 transport/"]
                    PREST["📄 rest.py"]
                    PWS["📄 websocket.py"]
                end
            end
        end
        
        subgraph Docs["📁 docs/"]
            SRS["📄 SRS.md"]
            CTM["📄 CODE_TRACEABILITY_MATRIX.md"]
            ARCH["📄 ARCHITECTURE_DIAGRAMS.md"]
        end
        
        SCHEMA["📄 schema.sql"]
        WRANG["📄 wrangler.toml"]
        PKG["📄 package.json"]
    end
```

---

## 10. Request Flow Diagram

```mermaid
flowchart LR
    subgraph Client
        REQ["HTTP Request"]
    end

    subgraph CloudflareEdge["Cloudflare Edge"]
        direction TB
        WKR["Worker"]
        
        subgraph Routing["Request Router"]
            AUTH_R["/api/auth/*"]
            USER_R["/api/users/*"]
            MSG_R["/api/messages/*"]
            GRP_R["/api/groups/*"]
            WS_R["/ws"]
        end
        
        subgraph Handlers["Handlers"]
            AUTH_H["AuthHandler"]
            USER_H["UserHandler"]
            MSG_H["MessageHandler"]
            GRP_H["GroupHandler"]
        end
        
        DO["Durable Object<br/>(WebSocket)"]
        DB[("D1 Database")]
    end

    REQ --> WKR
    WKR --> Routing
    
    AUTH_R --> AUTH_H
    USER_R --> USER_H
    MSG_R --> MSG_H
    GRP_R --> GRP_H
    WS_R --> DO
    
    AUTH_H --> DB
    USER_H --> DB
    MSG_H --> DB
    GRP_H --> DB
    DO --> DB
```

---

## 11. State Management Diagram

```mermaid
stateDiagram-v2
    [*] --> Disconnected
    
    Disconnected --> Connecting: Connect WebSocket
    Connecting --> Connected: Connection Established
    Connecting --> Disconnected: Connection Failed
    
    Connected --> Authenticated: Send Auth Message
    Authenticated --> Chatting: Select User/Group
    
    Chatting --> Typing: Start Typing
    Typing --> Chatting: Stop Typing (3s timeout)
    Chatting --> Sending: Send Message
    Sending --> Chatting: Message Sent
    
    state Chatting {
        [*] --> Idle
        Idle --> ReceivingMessage: Incoming Message
        ReceivingMessage --> Decrypting
        Decrypting --> DisplayMessage
        DisplayMessage --> Idle
    }
    
    Connected --> Disconnected: Connection Lost
    Authenticated --> Disconnected: Logout
    Chatting --> Authenticated: Back to List
```

---

## 12. Deployment Architecture

```mermaid
flowchart TB
    subgraph Development["Development Environment"]
        DEV_CODE["Source Code"]
        WRANGLER["Wrangler CLI"]
        LOCAL["Local Dev Server<br/>(wrangler dev)"]
    end

    subgraph Build["Build Process"]
        TS["TypeScript Compile"]
        VITE["Vite Build"]
        BUNDLE["Worker Bundle"]
    end

    subgraph Cloudflare["Cloudflare Platform"]
        subgraph Edge["Edge Network (300+ PoPs)"]
            W1["Worker Instance"]
            W2["Worker Instance"]
            W3["Worker Instance"]
        end
        
        subgraph Persistence["Persistence Layer"]
            D1_1[("D1 Primary")]
            D1_R[("D1 Replicas")]
            DO_S["DO Storage"]
        end
    end

    subgraph Users["End Users"]
        U1["🌍 User (US)"]
        U2["🌍 User (EU)"]
        U3["🌍 User (Asia)"]
    end

    DEV_CODE --> WRANGLER
    WRANGLER --> LOCAL
    WRANGLER --> Build
    Build --> Cloudflare
    
    U1 --> W1
    U2 --> W2
    U3 --> W3
    
    W1 --> D1_1
    W2 --> D1_R
    W3 --> D1_R
    W1 --> DO_S
    W2 --> DO_S
    W3 --> DO_S
```

---

## How to View These Diagrams

1. **VS Code:** Install "Markdown Preview Mermaid Support" extension
2. **GitHub:** Renders automatically in markdown preview
3. **Mermaid Live Editor:** https://mermaid.live
4. **Documentation Tools:** Docusaurus, MkDocs with mermaid plugin

---

**End of Architecture Diagrams**
