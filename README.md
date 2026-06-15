# Secure Self-Hosted Chat & File Sharing Client

A modern, multi-threaded TCP chat application built with Python and Tkinter, featuring a dark-themed UI. The system relies on custom TCP packet framing and robust, secure serialization to provide low-latency communication and safe file transfers.

## 🛠️ Key Technical Highlights

*   **Custom TCP Framing Protocol**: Solves the classic TCP stream segmentation (packet splitting/clumping) issue by prefixing every message with an 8-byte big-endian length header (`struct.pack('!Q', len(data))`).
*   **Safe Serialization (No Pickle Security Flaws)**: Replaced insecure pickle serialization with safe, standard JSON serialization [1]. Binary file uploads are dynamically encoded into Base64 strings to eliminate Remote Code Execution (RCE) vectors.
*   **Multi-Threaded Architecture**: Out-of-the-box support for hosting and joining. Main thread runs the Tkinter event loop, while background daemon threads handle inbound socket monitoring and state updates.
*   **File Transfer Engine**: Safely transfers files (up to 15MB) across clients with automatic sender filtering and native OS save dialogs.
*   **Modern Custom UI Theme**: Designed using customized Tkinter & TTK widgets, sporting a sophisticated dark mode color scheme.

---

## 🚀 Getting Started

### Prerequisites
Make sure you have Python 3 installed on your system.

### Running the App
Since this app uses native Python libraries, there are no external dependencies to install. 

1. **Clone the repository:**
   ```bash
   git clone https://github.com/mad808/secure-p2p-chat.git
   cd secure-p2p-chat