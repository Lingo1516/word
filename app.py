# === 步驟 4: 寫作 (智慧數據管制版) ===
elif st.session_state.step == 4:
    st.subheader("步驟 5：逐章撰寫")
    
    chapters = ["第一章 緒論", "第二章 文獻探討", "第三章 研究方法", "第四章 分析結果", "第五章 結論"]
    
    # 確保 content 是字典格式
    if 'content' not in st.session_state or not isinstance(st.session_state.content, dict):
        st.session_state.content = {}

    # 選擇章節
    selected_ch = st.selectbox("選擇要撰寫或檢視的章節", chapters)
    
    st.info(f"📍 目前選擇：{selected_ch}")

    # 撰寫按鈕
    if st.button(f"🚀 讓 AI 撰寫 {selected_ch}"):
        
        # === 關鍵修改：智慧數據管制 ===
        # 只有在寫「第四章」或「結論」時，才把數據餵給 AI
        # 其他章節 (緒論、文獻、方法) 強制隱藏數據，避免 AI 偷跑去寫分析結果
        sim_json = json.dumps(st.session_state.sim_data, ensure_ascii=False) if st.session_state.sim_data else "無"
        
        current_data_context = "本章節不涉及數據分析，請專注於理論與架構。"
        if "第四章" in selected_ch or "結論" in selected_ch:
            current_data_context = f"【模擬分析數據】：\n{sim_json}"
            
        # 針對不同章節的專屬指令
        instruction = ""
        if "第一章" in selected_ch:
            instruction = "請撰寫研究背景、動機與目的。絕對不要提及具體的分析數據結果。"
        elif "第二章" in selected_ch:
            instruction = "請進行文獻回顧與假說推導。絕對不要提及具體的分析數據結果。"
        elif "第三章" in selected_ch:
            instruction = "請詳細描述研究設計、變數定義與數學模型 (AHP/FCM等)。不要寫出結果。"
        elif "第四章" in selected_ch:
            instruction = "這是論文的核心。請務必引用上述的【模擬分析數據】，將表格數據轉化為文字分析，解釋各準則的權重與企業排名的意義。"
        
        prompt = f"""
        你是一個嚴謹的學術論文寫作助手。
        
        【任務目標】：請撰寫「{selected_ch}」的完整內容。
        【論文題目】：{st.session_state.final_title}
        【大綱架構】：{st.session_state.outline}
        {current_data_context}
        
        ⚠️ 嚴格規則：
        1. 請**只撰寫**「{selected_ch}」的內容，不要離題。
        2. {instruction}
        3. 請使用學術語氣 (Academic Tone)，並使用 Markdown 格式 (包含標題 #, ##)。
        
        請開始撰寫：
        """
        
        with st.spinner(f"AI 正在專注撰寫 {selected_ch} (已過濾干擾資訊)..."):
            st.session_state.content[selected_ch] = call_ai_api(prompt)
            st.rerun() # 強制刷新畫面

    st.divider()

    # --- 內容顯示區 ---
    if selected_ch in st.session_state.content:
        st.markdown(f"### 📄 {selected_ch} 草稿內容")
        st.markdown(st.session_state.content[selected_ch])
        
        # 貼心功能：重新生成按鈕
        if st.button("🔄 不滿意？重新撰寫此章節"):
            # 清除該章節內容並重跑
            del st.session_state.content[selected_ch]
            st.rerun()
    else:
        st.warning(f"⚠️ {selected_ch} 尚未撰寫。請點擊上方按鈕開始生成。")

    st.divider()
    
    # 下載區
    final_doc = f"# {st.session_state.final_title}\n\n"
    for ch in chapters:
        if ch in st.session_state.content:
            final_doc += f"## {ch}\n{st.session_state.content[ch]}\n\n"
            
    st.download_button("📥 下載全文 (.txt)", final_doc, "thesis_full.txt")
