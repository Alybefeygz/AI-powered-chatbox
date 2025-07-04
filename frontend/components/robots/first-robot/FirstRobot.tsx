"use client"

import type React from "react"
import { useState, useRef, useEffect } from "react"
import FirstRobotChatBox from "./FirstRobotChatBox"
import { useRobotChat } from "../../../hooks/use-api"
import { toast } from "sonner"

interface FirstRobotProps {
  onChatToggle: (robotId: string, isOpen: boolean) => void
  isOtherChatOpen: boolean
  isFloating?: boolean
}

interface Message {
  id: number
  text: string
  isUser: boolean
  timestamp: Date
  status?: 'loading' | 'ok' | 'error'
}

export default function FirstRobot({ onChatToggle, isOtherChatOpen, isFloating = false }: FirstRobotProps) {
  // Chat state
  const [isChatOpen, setIsChatOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      text: "Merhaba, ben **SidrexGPT**. **Sidrex** markasının sizler için geliştirdiği özel bir **yapay zekâ** asistanıyım.",
      isUser: false,
      timestamp: new Date(),
      status: 'ok',
    },
    {
      id: 2,
      text: "Size nasıl yardımcı olabilirim?",
      isUser: false,
      timestamp: new Date(),
      status: 'ok',
    },
  ])
  const [inputValue, setInputValue] = useState("")
  const [chatPosition, setChatPosition] = useState({ top: 0, left: 0 })

  // Robot Chat API integration
  const { sendMessage: sendChatMessage, loading: chatLoading } = useRobotChat('sidrexgpt')

  // Animation state
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 })
  const robotRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const [eyesVisible, setEyesVisible] = useState(true)
  const [isHovered, setIsHovered] = useState(false)

  // Track animation state to know when eyes are visible
  useEffect(() => {
    const interval = setInterval(() => {
      const animationDuration = isHovered || isChatOpen ? 2000 : 5000
      const currentTime = Date.now() % animationDuration
      const progress = currentTime / animationDuration

      // Eyes are visible from 0% to 70% when hovered/chat open, 0% to 80% when normal
      const eyeVisibilityThreshold = isHovered || isChatOpen ? 0.7 : 0.8
      setEyesVisible(progress < eyeVisibilityThreshold)
    }, 50)

    return () => clearInterval(interval)
  }, [isHovered, isChatOpen])

  // Mouse tracking effect - only when eyes are visible
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (robotRef.current && eyesVisible) {
        const rect = robotRef.current.getBoundingClientRect()
        const robotCenterX = rect.left + rect.width / 2
        const robotCenterY = rect.top + rect.height / 2

        // Calculate relative mouse position
        const deltaX = e.clientX - robotCenterX
        const deltaY = e.clientY - robotCenterY

        // Limit the eye movement range (maximum 2 pixels as specified)
        const maxMove = 2
        const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY)
        const limitedX = distance > 0 ? (deltaX / distance) * Math.min(distance / 100, maxMove) : 0
        const limitedY = distance > 0 ? (deltaY / distance) * Math.min(distance / 100, maxMove) : 0

        setMousePosition({ x: limitedX, y: limitedY })
      } else {
        // Reset position when eyes are not visible
        setMousePosition({ x: 0, y: 0 })
      }
    }

    window.addEventListener("mousemove", handleMouseMove)
    return () => window.removeEventListener("mousemove", handleMouseMove)
  }, [eyesVisible])

  // Close chat when other chat opens
  useEffect(() => {
    if (isOtherChatOpen && isChatOpen) {
      setIsChatOpen(false)
      setIsHovered(false)
    }
  }, [isOtherChatOpen, isChatOpen])

  const sendMessage = async () => {
    if (inputValue.trim() === "" || chatLoading) return

    const userMessage: Message = {
      id: Date.now(),
      text: inputValue,
      isUser: true,
      timestamp: new Date(),
      status: 'ok'
    }

    const loadingMessage: Message = {
        id: Date.now() + 1,
        text: "...",
        isUser: false,
        timestamp: new Date(),
        status: 'loading',
    }

    setMessages((prev) => [...prev, userMessage, loadingMessage])
    const messageText = inputValue
    setInputValue("")

    try {
      const response = await sendChatMessage(messageText)
      
      if (response && response.robot_response) {
        const botResponse: Message = {
          id: loadingMessage.id, // Use the same ID to update
          text: response.robot_response,
          isUser: false,
          timestamp: new Date(),
          status: 'ok'
        }
        setMessages((prev) => prev.map(msg => msg.id === loadingMessage.id ? botResponse : msg))
      } else {
        // Handle case where response is not as expected
        const errorResponse: Message = {
            id: loadingMessage.id,
            text: "Yanıt alınamadı, lütfen tekrar deneyin.",
            isUser: false,
            timestamp: new Date(),
            status: 'error',
        }
        setMessages((prev) => prev.map(msg => msg.id === loadingMessage.id ? errorResponse : msg));
      }
    } catch (error: any) {
      console.error('Chat error:', error)
      toast.error(error.message || 'Mesaj gönderilemedi')
      
      const errorResponse: Message = {
        id: loadingMessage.id,
        text: "Üzgünüm, şu anda bir sorun yaşıyorum. Lütfen daha sonra tekrar deneyin.",
        isUser: false,
        timestamp: new Date(),
        status: 'error'
      }
      setMessages((prev) => prev.map(msg => msg.id === loadingMessage.id ? errorResponse : msg));
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      sendMessage()
    }
  }

  const toggleChat = () => {
    if (!isChatOpen && buttonRef.current && !isFloating) {
      const rect = buttonRef.current.getBoundingClientRect()
      setChatPosition({
        top: rect.bottom - 480 + window.scrollY,
        left: rect.left - 450 + window.scrollX,
      })
    }
    const newChatState = !isChatOpen
    setIsChatOpen(newChatState)
    onChatToggle("first", newChatState)
  }

  return (
    <>
      <button
        ref={buttonRef}
        onClick={toggleChat}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        className={`w-24 h-24 bg-white border-2 border-gray-200 rounded-full shadow-2xl hover:shadow-xl transition-all duration-300 transform hover:scale-105 cursor-pointer flex items-center justify-center relative overflow-visible ${
          isChatOpen ? "robot-chat-active" : ""
        }`}
      >
        {/* Robot Mascot */}
        <div ref={robotRef} className={`robot-mascot-container ${isChatOpen ? "chat-active" : ""}`}>
          {/* Robot Head */}
          <div className="robot-head">
            {/* Robot Antenna */}
            <div className="robot-antenna"></div>

            {/* Robot Ears */}
            <div className="robot-ear robot-ear-left"></div>
            <div className="robot-ear robot-ear-right"></div>

            {/* Robot Face Screen */}
            <div className="robot-face">
              {/* Robot Eyes with mouse tracking */}
              <div
                className="robot-eye robot-eye-left"
                style={{
                  transform: eyesVisible ? `translate(${mousePosition.x}px, ${mousePosition.y}px)` : "none",
                }}
              ></div>
              <div
                className="robot-eye robot-eye-right"
                style={{
                  transform: eyesVisible ? `translate(${mousePosition.x}px, ${mousePosition.y}px)` : "none",
                }}
              ></div>

              {/* Robot Hands */}
              <div className="robot-hands"></div>

              {/* Robot Smile */}
              <div className="robot-smile"></div>
            </div>
          </div>
        </div>
      </button>

      {/* Chat Box */}
      {isChatOpen && (
        <FirstRobotChatBox
          messages={messages}
          inputValue={inputValue}
          setInputValue={setInputValue}
          sendMessage={sendMessage}
          handleKeyPress={handleKeyPress}
          onClose={() => setIsChatOpen(false)}
          position={chatPosition}
          isFloating={isFloating}
          isLoading={chatLoading}
        />
      )}
    </>
  )
}
