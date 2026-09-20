import streamlit as st
from skill_erosion.ui import shell, page_header, reset_context, error, empty_state, note, capability_report_pdf
from skill_erosion.agents.parent_chat.agent import parent_chat


def main():
    pipeline = shell("Parent")
    page_header("Parent", "A little context. A helpful conversation.",
                "A supportive view of your child's learning, with room to ask what you can do at home.")
    accounts = pipeline.repo.parent_accounts()
    if not accounts:
        st.info("Ask the teacher to load the pilot dataset and link a parent account before opening a learning update.")
        st.stop()
    with st.sidebar:
        account = st.selectbox("Parent account", accounts, key="parent_account")
        note("Your family's view", "Each account is linked to one learner. Learning updates stay within that link.")
        note("Synthetic pilot", "Local demonstration accounts. Real deployments require authenticated sign-in.")

    # This is the sole resolution path. No caller-supplied student identifier is accepted by the UI.
    student = pipeline.repo.get_linked_student(account)
    reset_context((account,))
    attempts = pipeline.repo.history_for_parent(account)
    skill = sorted({a.skill_id for a in attempts})[0]
    update, conversation = st.columns([1.1, 1], gap="large")
    journey = st.session_state.get("parent_journey")

    with update:
        with st.container(key="parent_update"):
            st.subheader("Your child's learning update")
            st.caption("A little history can make the next conversation easier.")
            if st.button("View learning update", key="view_update", type="primary"):
                try:
                    with st.spinner("Preparing your learning update..."):
                        st.session_state["parent_journey"] = pipeline.for_parent(account, skill)
                    journey = st.session_state["parent_journey"]
                except Exception as exc:
                    error(exc)
            if journey:
                st.write(parent_chat("learning progress update", journey))
                independent = {a.checkpoint_id for a in attempts if a.assistance == "unassisted" and a.skill_id == skill}
                followup = {a.checkpoint_id for a in attempts if a.origin == "follow_up" and a.skill_id == skill}
                a, b = st.columns(2)
                a.metric("Independent check-ins", len(independent))
                b.metric("Follow-up check-ins", len(followup))
                st.caption("Counts describe this learning history. Your teacher can provide the wider context.")
            else:
                empty_state("Understand the pattern",
                            "See how supported practice and independent work are developing, and where a little encouragement could help.")
            try:
                pdf_bytes = capability_report_pdf(pipeline, student)
                st.download_button("Download full capability report (PDF)", pdf_bytes,
                                   file_name=f"gaptrace-capability-{student}.pdf", mime="application/pdf",
                                   key="download_capability", width="stretch")
                st.caption("Covers every skill this learner has history for, with a chart of the latest independent score.")
            except Exception as exc:
                error(exc)
        with st.container(key="parent_help"):
            st.subheader("Keep it a conversation")
            st.write("Ask your child to explain one small part of what they are learning. Give them space to think before offering help.")
            st.caption("The aim is confidence and understanding, at their pace.")

    with conversation:
        st.subheader("Ask about learning at home")
        st.caption("Ask how to help with practice, or what the recent learning pattern means.")
        with st.form("parent_question"):
            question = st.text_input("Ask a question", key="question", placeholder="How can I help with practice?")
            asked = st.form_submit_button("Ask", type="primary")
        if asked:
            if not question.strip():
                st.warning("Write a question first.")
            else:
                try:
                    with st.spinner("Finding useful context..."):
                        journey = journey or pipeline.for_parent(account, skill)
                        st.session_state["parent_journey"] = journey
                        st.session_state["parent_answer"] = parent_chat(question, journey, pipeline.vectors)
                    st.rerun()
                except Exception as exc:
                    error(exc)
        if st.session_state.get("parent_answer"):
            with st.container(key="parent_answer"):
                st.markdown("**Learning companion**")
                st.write(st.session_state["parent_answer"])
        else:
            st.caption("You might ask: What does this pattern mean? How can we make practice feel less frustrating?")


main()
